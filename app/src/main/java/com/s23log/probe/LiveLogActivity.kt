package com.s23log.probe

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.Intent
import android.content.pm.ActivityInfo
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.SurfaceHolder
import android.view.SurfaceView
import android.view.WindowManager
import android.widget.*
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.s23log.probe.core.LiveLogOutput
import com.s23log.probe.core.RawJson
import com.s23log.probe.live.LiveLogSession
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.UUID
import java.util.concurrent.Executors

/** Explicit experimental mode, isolated from the existing direct SDR/HLG camera. */
@android.annotation.TargetApi(33)
class LiveLogActivity:Activity(),SurfaceHolder.Callback {
    private val store get()=(application as S23Application).liveLog
    private lateinit var status:TextView
    private lateinit var profileLabel:TextView
    private lateinit var surface:SurfaceView
    private lateinit var frame:FrameLayout
    private lateinit var fps:Spinner
    private lateinit var outputs:Spinner
    private lateinit var focus:EditText
    private lateinit var provisional:CheckBox
    private lateinit var clipping:CheckBox
    private lateinit var prepare:Button
    private lateinit var record:Button
    private lateinit var stop:Button
    private lateinit var probe:Button
    private lateinit var saved:Button
    private lateinit var imported:Button
    private var choices=emptyList<LiveLogOutput>()
    private var profile:JSONObject?=null
    private var profileName:String?=null
    private var surfaceReady=false
    private var visible=false
    private var importBusy=false
    private var viewWidth=1920
    private var viewHeight=1080
    private val io=Executors.newSingleThreadExecutor()
    private val observer:(LiveLogSession.State)->Unit={render(it)}
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        if(Build.VERSION.SDK_INT<33){Toast.makeText(this,"Live Log requires Android 13 or newer",Toast.LENGTH_LONG).show();finish();return}
        WindowCompat.setDecorFitsSystemWindows(window,false)
        val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(12),dp(8),dp(12),dp(8))};setContentView(root)
        ViewCompat.setOnApplyWindowInsetsListener(root){v,i->val b=i.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout());val keyboard=i.getInsets(WindowInsetsCompat.Type.ime());v.setPadding(b.left+dp(12),b.top+dp(8),b.right+dp(12),maxOf(b.bottom,keyboard.bottom)+dp(8));i}
        root.addView(TextView(this).apply{text="Live RAW-derived LogC3";textSize=23f;setPadding(0,dp(4),0,dp(8))})
        frame=FrameLayout(this);surface=SurfaceView(this);surface.holder.addCallback(this);surface.holder.setFixedSize(640,360)
        frame.addView(surface,FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));root.addView(frame,LinearLayout.LayoutParams(-1,dp(200)))
        frame.addOnLayoutChangeListener{_,_,_,_,_,_,_,_,_->fitPreview()}
        val body=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
        root.addView(ScrollView(this).apply{addView(body)},LinearLayout.LayoutParams(-1,0,1f))
        fun text(value:String)=TextView(this).apply{text=value;textSize=15f;setPadding(0,dp(6),0,dp(6));body.addView(this)}
        fun button(label:String,action:()->Unit)=Button(this).apply{text=label;minHeight=dp(48);setOnClickListener{action()};body.addView(this,LinearLayout.LayoutParams(-1,-2))}
        text("Experimental video-only mode. RAW → GPU → LogC3/AWG3. No firmware changes, 4K/8K or ARRI sensor-range claims. The corrected preview is a practical SDR view, not a calibrated display. Leaving this screen stops capture and finalizes retained footage.")
        status=text(store.state.message)
        probe=button("Test Log recording backend") {store.testBackend(selectedFps())}
        button("Share latest backend / recording report") {store.state.report?.takeIf{it.isFile}?.let{share(listOf(it))}}
        profileLabel=text("No profile selected. Create a profile through Retained RAW sequences → Develop as LogC3, or import a matching profile.")
        saved=button("Choose saved live colour profile") {chooseProfile()}
        imported=button("Import live colour profile") {startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply{addCategory(Intent.CATEGORY_OPENABLE);type="*/*";putExtra(Intent.EXTRA_MIME_TYPES,arrayOf("application/json","text/plain","application/octet-stream"))},201)}
        text("Requested sensor cadence")
        fps=Spinner(this).apply{adapter=ArrayAdapter(this@LiveLogActivity,android.R.layout.simple_spinner_dropdown_item,listOf("24 fps","30 fps"));contentDescription="Live sensor frame rate"};body.addView(fps)
        text("Explicit source crop and output (at most 1080p)")
        outputs=Spinner(this).apply{contentDescription="Live source crop and output"};body.addView(outputs)
        text("Manual focus in diopters: 0 means infinity. Sensor ISO/shutter and software white balance come from the selected profile; they are not changed silently.")
        focus=EditText(this).apply{setText("0");hint="Focus diopters";contentDescription="Manual focus in diopters";inputType=InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL};body.addView(focus)
        provisional=CheckBox(this).apply{text="Allow provisional, unmeasured colour profile"};body.addView(provisional)
        clipping=CheckBox(this).apply{text="Allow final output clipping; clipped frames are reported"};body.addView(clipping)
        body.addView(Switch(this).apply{text="Show Log signal instead of corrected preview";setOnCheckedChangeListener{_,value->store.viewing(value)}})
        prepare=button("Prepare live RAW preview") {preparePreview()}
        text("Each preparation rechecks GPU and 10-bit codec precision. A missing route stays unavailable. RAW copying/P010 transfer are not zero-copy. Preview frames may be skipped, but recording overload stops explicitly. Bounded timestamp index: 18,000 recorded frames; no audio in this milestone.")
        button("Retained live exports / partial files") {retained()}
        button("Share last checked movie + sidecar") {store.state.media?.takeIf{it.isFile}?.let{share(listOf(it)+listOfNotNull(store.state.report?.takeIf(File::isFile)))}}
        button("Return to existing camera") {store.stop();finish()}
        val dock=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        record=Button(this).apply{text="Record LogC3";minHeight=dp(52);setOnClickListener{store.record()}}
        stop=Button(this).apply{text="Stop";minHeight=dp(52);setOnClickListener{store.stop()}}
        dock.addView(record,LinearLayout.LayoutParams(0,-2,1f));dock.addView(stop,LinearLayout.LayoutParams(0,-2,1f));root.addView(dock)
        savedInstanceState?.getString("profileName")?.let{val f=File(filesDir,"exports/raw-profiles/$it");if(f.isFile && f.name.matches(Regex("profile-[0-9a-f-]+\\.json")))runCatching{load(f)}}
        render(store.state)
    }
    override fun onStart(){super.onStart();if(Build.VERSION.SDK_INT>=33){visible=true;store.observe(observer)}}
    override fun onStop(){if(Build.VERSION.SDK_INT>=33){visible=false;store.stop();store.remove(observer)};super.onStop()}
    override fun onDestroy(){io.shutdown();super.onDestroy()}
    override fun onSaveInstanceState(outState:Bundle){outState.putString("profileName",profileName);super.onSaveInstanceState(outState)}
    override fun surfaceCreated(holder:SurfaceHolder){surfaceReady=true;if(::record.isInitialized)render(store.state)}
    override fun surfaceChanged(holder:SurfaceHolder,format:Int,width:Int,height:Int){surfaceReady=true}
    override fun surfaceDestroyed(holder:SurfaceHolder){surfaceReady=false;store.stop()}
    private fun selectedFps()=if(::fps.isInitialized && fps.selectedItemPosition==1)30 else 24
    private fun fitPreview(){
        if(frame.width<=0 || frame.height<=0)return
        val aspect=viewWidth.toDouble()/viewHeight
        val w=minOf(frame.width,(frame.height*aspect).toInt());val h=(w/aspect).toInt()
        val old=surface.layoutParams as FrameLayout.LayoutParams
        if(old.width!=w || old.height!=h)surface.layoutParams=FrameLayout.LayoutParams(w,h,Gravity.CENTER)
    }
    private fun render(s:LiveLogSession.State){
        if(!::record.isInitialized)return
        status.text=s.message
        prepare.isEnabled=!s.busy && !importBusy && surfaceReady && choices.isNotEmpty()
        probe.isEnabled=!s.busy && !importBusy;saved.isEnabled=!s.busy && !importBusy;imported.isEnabled=!s.busy && !importBusy
        listOf(fps,outputs,focus,provisional,clipping).forEach{it.isEnabled=!s.busy && !importBusy}
        record.isEnabled=s.preview && !s.recording;stop.isEnabled=s.busy
        record.text=if(s.recording)"Recording LogC3" else "Record LogC3"
        if(s.busy){window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);requestedOrientation=ActivityInfo.SCREEN_ORIENTATION_LOCKED}
        else{window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);requestedOrientation=ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED}
    }
    private fun load(file:File){
        require(file.length() in 1..1_048_576)
        val json=RawJson.parse(file.readBytes());require(json.getString("kind")=="raw-colour-profile")
        val options=LiveLogOutput.choices(RawJson.ints(json,"crop",4)).filter{it.width>=600}
        require(options.isNotEmpty()){"Profile crop has no supported live output"}
        profile=json;profileName=file.name;choices=options
        outputs.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,options.map{it.label})
        profileLabel.text="${file.name}\n${json.getJSONObject("source")}\nProfile ${json.getJSONObject("calibration").getString("status")} · ISO ${json.getLong("iso")} · ${json.getLong("exposureNs")} ns"
        provisional.isChecked=false;clipping.isChecked=false;render(store.state)
    }
    private fun chooseProfile(){
        val files=File(filesDir,"exports/raw-profiles").listFiles().orEmpty().filter{it.isFile && it.name.matches(Regex("profile-[0-9a-f-]+\\.json")) && it.length() in 1..1_048_576}.sortedByDescending{it.lastModified()}.take(128)
        AlertDialog.Builder(this).setTitle("Saved profiles; exact device binding checked before capture")
            .setItems(files.map{it.name}.toTypedArray()){_,i->runCatching{load(files[i])}.onFailure{status.text=it.message}}
            .setNegativeButton("Close",null).show()
    }
    @Deprecated("Activity callback retained for minimum SDK")
    override fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?){
        super.onActivityResult(requestCode,resultCode,data)
        if(requestCode!=201 || resultCode!=RESULT_OK)return
        val uri=data?.data ?: return;importBusy=true;render(store.state)
        io.execute{
            val result=runCatching{
                val bytes=contentResolver.openInputStream(uri)?.use{input->val out=ByteArrayOutputStream();val buffer=ByteArray(16384)
                    while(true){val n=input.read(buffer);if(n<0)break;require(out.size()+n<=1_048_576){"Profile exceeds 1 MiB"};out.write(buffer,0,n)};out.toByteArray()} ?: error("Profile cannot be read")
                RawJson.parse(bytes);val dir=File(filesDir,"exports/raw-profiles");check(dir.isDirectory || dir.mkdirs())
                File(dir,"profile-${UUID.randomUUID()}.json").apply{writeBytes(bytes)}
            }
            runOnUiThread{importBusy=false;if(!isDestroyed){result.onSuccess{runCatching{load(it)}.onFailure{e->status.text=e.message}}.onFailure{status.text=it.message};render(store.state)}}
        }
    }
    private fun preparePreview(){
        if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED){requestPermissions(arrayOf(Manifest.permission.CAMERA),202);return}
        runCatching {
            val json=requireNotNull(profile){"Select a matching colour profile"};val option=choices[outputs.selectedItemPosition]
            require(surfaceReady && visible){"Preview surface unavailable"}
            viewWidth=option.width;viewHeight=option.height;fitPreview();surface.holder.setFixedSize(640,(640L*option.height/option.width).toInt())
            val orientation=windowManager.defaultDisplay.rotation*90
            store.prepare(json,option,selectedFps(),focus.text.toString().toFloat(),provisional.isChecked,clipping.isChecked,surface.holder.surface,orientation)
        }.onFailure{status.text=it.message}
    }
    private fun retained(){
        if(store.state.busy){status.text="Stop live work before sharing retained files.";return}
        val files=store.directory.listFiles().orEmpty().filter{it.isFile && it.extension in setOf("mp4","json")}.sortedByDescending{it.lastModified()}.take(128)
        AlertDialog.Builder(this).setTitle("Private exports; partial files are unverified and may not play")
            .setItems(files.map{it.name}.toTypedArray()){_,i->share(listOf(files[i]))}.setNegativeButton("Close",null).show()
    }
    private fun share(files:List<File>){
        val uris=ArrayList(files.map{FileProvider.getUriForFile(this,"$packageName.files",it)})
        if(uris.isEmpty())return
        startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND_MULTIPLE).apply{
            type="application/octet-stream";putParcelableArrayListExtra(Intent.EXTRA_STREAM,uris);addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            clipData=ClipData.newUri(contentResolver,"Live Log export",uris.first()).also{c->uris.drop(1).forEach{c.addItem(ClipData.Item(it))}}
        },"Share Log video with colour sidecar"))
    }
    private fun dp(value:Int)=(value*resources.displayMetrics.density).toInt()
}
