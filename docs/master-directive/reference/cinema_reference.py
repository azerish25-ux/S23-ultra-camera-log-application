"""Original executable host reference contracts for the S23 cinema directive.

Python 3.11+, standard library only. Not an Android camera implementation.
LogC3 EI800 exposure-domain constants follow ARRI's 2017 VFX specification.
The toy density curve and white Gaussian noise are test scaffolds, NOT a
calibrated Kodak stock or a physically complete film-grain implementation.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

CUT = 0.010591
A, B, C, D, E, F = 5.555556, 0.052272, 0.247190, 0.385537, 5.367655, 0.092809


def finite(value: float, name: str = 'value') -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f'{name} must be finite')
    return value


def integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name} must be an integer, not bool')
    return value


def logc3_encode(value: float) -> float:
    x = finite(value)
    return finite(C * math.log10(A*x+B) + D if x > CUT else E*x+F, "encoded LogC3")


def logc3_decode(value: float) -> float:
    y = finite(value)
    try:
        x = (10**((y-D)/C)-B)/A if y > E*CUT+F else (y-F)/E
    except OverflowError as exc:
        raise ValueError('Log input exceeds finite reference domain') from exc
    return finite(x, 'decoded exposure')


def normalize_raw(code: float, black: float, white: float) -> float:
    code, black, white = finite(code), finite(black), finite(white)
    if white <= black:
        raise ValueError('White level must exceed black level')
    return finite(finite(code-black, "RAW numerator") / finite(white-black, "RAW denominator"), "normalized RAW")


def quantize_luma10(value: float, allow_clip: bool = False) -> int:
    x = finite(value)
    if not 0 <= x <= 1:
        if not allow_clip:
            raise ValueError('Clipping requires explicit caller authorization')
        x = min(1.0, max(0.0, x))
    # Defined half-up rounding; this is luma only, not a chroma formula.
    return int(math.floor(64+876*x+0.5))


def pack_p010_row(codes: Iterable[int], row_stride: int) -> bytes:
    values = list(codes)
    integer(row_stride, 'row_stride')
    if row_stride < 2*len(values) or row_stride % 2:
        raise ValueError('Stride must be even and large enough')
    result = bytearray(row_stride)
    for i, code in enumerate(values):
        integer(code, 'code')
        if not 0 <= code <= 1023:
            raise ValueError('Ten-bit code out of range')
        result[2*i:2*i+2] = (code << 6).to_bytes(2, 'little')
    return bytes(result)


def unpack_p010_row(data: bytes, width: int) -> list[int]:
    integer(width, 'width')
    if width < 0 or len(data) < 2*width:
        raise ValueError('Insufficient row data')
    values=[]
    for i in range(width):
        word = int.from_bytes(data[2*i:2*i+2], 'little')
        if word & 63:
            raise ValueError('P010 sample has nonzero low six bits')
        values.append(word >> 6)
    return values


def pts_us(index: int, rate_num: int, rate_den: int) -> int:
    for value, name in ((index,'index'),(rate_num,'rate_num'),(rate_den,'rate_den')):
        integer(value,name)
    if index < 0 or rate_num <= 0 or rate_den <= 0:
        raise ValueError('Invalid frame index or rational frame rate')
    return index*rate_den*1_000_000//rate_num


def pair_exact(timestamps: Iterable[int], metadata: Mapping[int, Any]) -> list[Any]:
    ts = list(timestamps)
    if any(isinstance(t,bool) or not isinstance(t,int) or t<0 for t in ts):
        raise ValueError('Sensor timestamps must be nonnegative integers')
    if any(a >= b for a,b in zip(ts, ts[1:])):
        raise ValueError('Sensor timestamps must be strictly increasing')
    missing=[t for t in ts if t not in metadata]
    if missing:
        raise ValueError(f'Missing exact metadata for {missing[0]}')
    return [metadata[t] for t in ts]


def coc_mm(focal_mm: float, f_number: float, focus_mm: float, object_mm: float) -> float:
    """Signed thin-lens circle diameter at the focused image plane.

    Positive = farther than focus, negative = nearer. A finite virtual focus
    is required. Object distance may be positive infinity. Units are millimetres.
    f-number controls aperture geometry; a T-stop is not substituted here.
    """
    f,n,s=finite(focal_mm),finite(f_number),finite(focus_mm)
    u=float(object_mm)
    if f<=0 or n<=0 or s<=f or math.isnan(u) or u<=f:
        raise ValueError('Invalid thin-lens geometry')
    denominator = finite(n*(s-f), "optical denominator")
    if denominator <= 0: raise ValueError("Optical denominator underflow")
    return finite(f*f/denominator * (1-s/u), "circle of confusion")


def coc_pixels(diameter_mm: float, gate_width_mm: float, output_width: int) -> float:
    d,w=finite(diameter_mm),finite(gate_width_mm)
    integer(output_width,'output_width')
    if w<=0 or output_width<=0:
        raise ValueError('Gate and output width must be positive')
    return d*output_width/w


@dataclass(frozen=True)
class DepthSample:
    value: float
    units: str


def metric_distance(sample: DepthSample) -> float:
    if sample.units!='metres':
        raise ValueError('Relative depth requires a validated metric calibration')
    value=finite(sample.value)
    if value<=0: raise ValueError('Depth must be positive')
    return value


def focal_for_fov(gate_width_mm: float, horizontal_degrees: float) -> float:
    g,a=finite(gate_width_mm),finite(horizontal_degrees)
    if g<=0 or not 0<a<180: raise ValueError('Invalid gate or field of view')
    return g/(2*math.tan(math.radians(a)/2))


def temporal_depth(current: float, reprojected_previous: float,
                   history_weight: float, occluded: bool=False) -> float:
    a,b,w=finite(current),finite(reprojected_previous),finite(history_weight)
    if a<=0 or b<=0 or not 0<=w<=1: raise ValueError('Invalid depth or history weight')
    # Caller must supply already reprojected, scale-aligned depth. This helper
    # does not estimate optical flow, detect occlusions, or establish metres.
    return a if occluded else (1-w)*a+w*b


def exposure_seconds(angle: float, rate_num: int, rate_den: int) -> float:
    a=finite(angle)
    integer(rate_num,'rate_num'); integer(rate_den,'rate_den')
    if not 0<a<=360 or rate_num<=0 or rate_den<=0:
        raise ValueError('Invalid shutter angle or frame rate')
    return a/360*rate_den/rate_num


@dataclass(frozen=True)
class ModeEvidence:
    advertised: bool
    configured: bool
    samples_received: bool
    independently_decoded: bool
    physical_protocol_passed: bool

    def __post_init__(self) -> None:
        if any(type(value) is not bool for value in (
            self.advertised, self.configured, self.samples_received,
            self.independently_decoded, self.physical_protocol_passed
        )):
            raise ValueError("Evidence fields require actual booleans")

    @property
    def certified(self) -> bool:
        # Simplified conjunction for one exact configuration, not a production
        # certification policy. Production additionally binds hashes and dates.
        return all((self.advertised,self.configured,self.samples_received,
                    self.independently_decoded,self.physical_protocol_passed))


def validate_lineage(origin: str, label: str, encoded_bits: int) -> None:
    permitted = {
        'RAW_SENSOR': {'RAW_DERIVED_LOG','RAW_DERIVED_LOOK'},
        'HLG10': {'HLG_DERIVED_LOG','HLG_DERIVED_LOOK'},
        'SDR8': {'SDR_DERIVED_LOOK'},
    }
    if origin not in permitted or label not in permitted[origin]:
        raise ValueError('Output label contradicts source lineage')
    if encoded_bits not in (8,10,12,16):
        raise ValueError('Unrecognized storage precision')
    if label.endswith('_LOG') and encoded_bits<10:
        raise ValueError('This project requires at least ten-bit Log delivery')


def canonical_json(value: Any) -> bytes:
    # This local canonical form is NOT a claim to implement RFC 8785.
    return json.dumps(value,sort_keys=True,separators=(',',':'),
                      ensure_ascii=False,allow_nan=False).encode('utf-8')


def resume_key(source_hash: str, model_hash: str, graph_hash: str, version: str) -> str:
    parts=[source_hash,model_hash,graph_hash,version]
    if any(not isinstance(x,str) or not x for x in parts):
        raise ValueError('All identities must be nonempty strings')
    return hashlib.sha256(canonical_json(parts)).hexdigest()


def atomic_json_write(destination: Path, value: Any) -> None:
    """Same-directory replacement reference; Android provider semantics differ."""
    payload=canonical_json(value)  # Validate BEFORE modifying any files.
    destination=Path(destination)
    fd,name=tempfile.mkstemp(prefix='.'+destination.name+'.',dir=destination.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(name,destination)
        # Directory fsync is intentionally not claimed by this portable helper.
        # Crash-durable production journals need filesystem-specific validation.
    finally:
        try: os.unlink(name)
        except FileNotFoundError: pass


def grain_sample(seed: int, frame: int, x: int, y: int, channel: int) -> float:
    values=(seed,frame,x,y,channel)
    for v in values: integer(v,'counter')
    digest=hashlib.sha256(canonical_json(values)).digest()
    u=(int.from_bytes(digest[:8],'big')+0.5)/2**64
    v=(int.from_bytes(digest[8:16],'big')+0.5)/2**64
    u=min(1-2**-53,max(2**-53,u))
    return math.sqrt(-2*math.log(u))*math.cos(2*math.pi*v)


def toy_density(exposure: float) -> float:
    x=finite(exposure)
    if x<=0: raise ValueError('Toy sensitometry requires positive exposure')
    z=math.log10(x)
    # Stable logistic: abstract monotonic fixture, not manufacturer calibration.
    p=1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))
    return 0.1+2.8*p


def transmittance(density: float) -> float:
    return 10**(-finite(density))


def validate_claim(status: str, references: list[str]) -> None:
    if status not in {'documented','reconstructed','unknown','contradicted'}:
        raise ValueError('Unknown evidence status')
    if status in {'documented','contradicted'} and not references:
        raise ValueError('Documented and contradicted claims need references')


@dataclass(frozen=True)
class RecorderState:
    phase: str='IDLE'
    generation: int=0
    expected: frozenset[str]=field(default_factory=frozenset)
    seen: frozenset[str]=field(default_factory=frozenset)


def reduce_recorder(state: RecorderState, event: str, generation: int,
                    track: str|None=None, expected: tuple[str,...]=('video',)) -> RecorderState:
    if event not in {'start','sample','stop','finalize','fail'}:
        raise ValueError('Unknown recorder event')
    integer(generation,'generation')
    if event=='start':
        if state.phase not in {'IDLE','FINALIZED','ERROR'} or generation<=state.generation:
            raise ValueError('Cannot start this generation')
        tracks=frozenset(expected)
        if not tracks or not tracks<={'video','audio'} or 'video' not in tracks:
            raise ValueError('Invalid selected track set')
        return RecorderState('STARTING',generation,tracks,frozenset())
    if generation!=state.generation:
        return state
    if event=='sample':
        if state.phase not in {'STARTING','RECORDING'}: return state
        if track not in state.expected: raise ValueError('Unexpected track')
        seen=state.seen|{track}
        phase='RECORDING' if seen==state.expected else 'STARTING'
        return RecorderState(phase,generation,state.expected,seen)
    if event=='stop' and state.phase in {'STARTING','RECORDING'}:
        return RecorderState('STOPPING',generation,state.expected,state.seen)
    if event=='finalize' and state.phase=='STOPPING':
        return RecorderState('FINALIZED',generation,state.expected,state.seen)
    if event=='fail':
        return RecorderState('ERROR',generation,state.expected,state.seen)
    return state
