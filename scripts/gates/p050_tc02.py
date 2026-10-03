"""TC-P050-02 CFA and crop parity.

Intervention: Use every supported mosaic pattern with odd and even crop origins
and distinct channel values.
Expected: Maintain correct channel identity and interpolation coordinates across
the transformed image.
Negative: Resetting mosaic parity after a crop must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P050-02"
INTERVENTION = (
    "Use every supported mosaic pattern with odd and even crop origins and distinct "
    "channel values."
)
EXPECTED = (
    "Maintain correct channel identity and interpolation coordinates across the "
    "transformed image."
)
NEGATIVE = "Resetting mosaic parity after a crop must fail."

_CFAS = ("RGGB", "BGGR", "GRBG", "GBRG")
_PHASE = {
    "RGGB": ("R", "G", "G", "B"),
    "BGGR": ("B", "G", "G", "R"),
    "GRBG": ("G", "R", "B", "G"),
    "GBRG": ("G", "B", "R", "G"),
}
_SITES = ("interior", "border", "padded", "rotated")
_ROTATIONS = (0, 90, 180, 270)
_PAYLOAD_KEYS = (
    "cfa",
    "cropLeft",
    "cropTop",
    "width",
    "height",
    "rowPadding",
    "red",
    "green",
    "blue",
    "site",
    "probeX",
    "probeY",
    "resetParity",
    "rotation",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "parity_held")
_FORBIDDEN = {"qualified", "allowed"}


def _channel(cfa: str, x: int, y: int) -> str:
    return _PHASE[cfa][(y % 2) * 2 + (x % 2)]


def evaluate(payload: dict) -> dict:
    """Keep carried CFA identity. Resetting parity after a crop is rejected."""
    fields = _payload(payload)
    cfa = fields["cfa"]
    left = fields["cropLeft"]
    top = fields["cropTop"]
    width = fields["width"]
    height = fields["height"]
    codes = {"R": fields["red"], "G": fields["green"], "B": fields["blue"]}
    rows: list[str] = []
    for y in range(height):
        letters = []
        for x in range(width):
            letters.append(_channel(cfa, left + x, top + y))
        rows.append("".join(letters))
    identity = "/".join(rows)
    probe_x = fields["probeX"]
    probe_y = fields["probeY"]
    carried = _channel(cfa, left + probe_x, top + probe_y)
    reset = _channel(cfa, probe_x, probe_y)
    sensor_x = left + probe_x
    sensor_y = top + probe_y
    preserved = [
        f"cfa:{cfa}",
        f"crop:{left},{top}",
        f"identity:{identity}",
        f"probe:{probe_x},{probe_y}:channel:{carried}:sensor:{sensor_x},{sensor_y}",
        f"codes:{codes['R']},{codes['G']},{codes['B']}",
        f"padding:{fields['rowPadding']}",
        f"rotation:{fields['rotation']}",
        f"site:{fields['site']}",
    ]
    if fields["resetParity"]:
        reasons = [
            EXPECTED,
            NEGATIVE,
            "mosaic parity was not reset after the crop",
            f"reset-label:{reset}",
            f"carried-label:{carried}",
        ]
        return _result(
            "rejected",
            reasons,
            ["mosaic-parity-reset"],
            preserved,
            ["parity was not reset"],
        )
    reasons = [
        EXPECTED,
        f"channel {carried} at sensor {sensor_x},{sensor_y}",
        "interpolation coordinate uses the original CFA origin",
        f"identity:{identity}",
    ]
    if fields["site"] == "padded":
        reasons.append("padded samples were not interpreted")
    if fields["site"] == "border":
        reasons.append("border pixel kept its carried channel")
    if fields["site"] == "rotated":
        reasons.append("developed RGB rotated after interpretation")
    return _result("parity_held", reasons, [], preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    cfa = payload["cfa"]
    if cfa not in _CFAS:
        raise ValueError("cfa must be a supported mosaic")
    width = _dim(payload["width"], "width")
    height = _dim(payload["height"], "height")
    left = _nonneg(payload["cropLeft"], "cropLeft")
    top = _nonneg(payload["cropTop"], "cropTop")
    padding = _nonneg(payload["rowPadding"], "rowPadding")
    red = _code(payload["red"], "red")
    green = _code(payload["green"], "green")
    blue = _code(payload["blue"], "blue")
    codes = (red, green, blue)
    if len(set(codes)) != 3:
        raise ValueError("channel codes must be distinct")
    gaps = [abs(codes[i] - codes[j]) for i in range(3) for j in range(i + 1, 3)]
    if min(gaps) < 100:
        raise ValueError("channel codes must be far apart")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site must be interior, border, padded, or rotated")
    probe_x = _nonneg(payload["probeX"], "probeX")
    probe_y = _nonneg(payload["probeY"], "probeY")
    if probe_x >= width or probe_y >= height:
        raise ValueError("probe must lie inside the crop")
    rotation = payload["rotation"]
    if rotation not in _ROTATIONS:
        raise ValueError("rotation must be 0, 90, 180, or 270")
    reset = payload["resetParity"]
    if type(reset) is not bool:
        raise ValueError("resetParity must be a bool")
    on_border = probe_x in (0, width - 1) or probe_y in (0, height - 1)
    if site == "border" and not on_border:
        raise ValueError("border site requires a border probe")
    if site == "interior" and (on_border or rotation != 0):
        raise ValueError("interior site requires an interior probe and no rotation")
    if site == "padded" and padding <= 0:
        raise ValueError("padded site requires row padding")
    if site == "rotated" and rotation == 0:
        raise ValueError("rotated site requires a developed rotation")
    return {
        "cfa": cfa,
        "cropLeft": left,
        "cropTop": top,
        "width": width,
        "height": height,
        "rowPadding": padding,
        "red": red,
        "green": green,
        "blue": blue,
        "site": site,
        "probeX": probe_x,
        "probeY": probe_y,
        "resetParity": reset,
        "rotation": rotation,
    }


def _dim(value: object, label: str) -> int:
    if type(value) is not int or value < 2 or value > 16:
        raise ValueError(label + " must be an int from 2 through 16")
    return value


def _nonneg(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(label + " must be a non-negative int")
    return value


def _code(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(label + " must be a non-negative int")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("parity decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
