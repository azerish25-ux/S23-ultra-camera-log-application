package com.s23log.probe

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.Intent
import android.graphics.*
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.*
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.s23log.probe.develop.RawDevelopmentStore
import java.io.File
import kotlin.math.roundToInt

/** Offline RAW development stays separate from camera capture and display-preview transforms. */
class RawDevelopActivity:Activity() {
    private val store get()=(application as S23Application).rawDevelopment
    private lateinit var status:TextView
    private lateinit var profileStatus:TextView
    private lateinit var selectionStatus:TextView
    private lateinit var preview:GreySelectionView
    private lateinit var scale:Spinner
    private lateinit var provisional:CheckBox
    private lateinit var clipping:CheckBox
    private lateinit var importButton:Button
    private lateinit var savedButton:Button
    private lateinit var deriveButton:Button
    private lateinit var exportButton:Button
    private lateinit var cancelButton:Button
    private lateinit var shareButton:Button
    private lateinit var profileShare:Button
    private lateinit var retained:Button
    private lateinit var attemptReports:Button
    private lateinit var coordinateButton:Button
    private var grey:IntArray?=null
    private var divisors=listOf(1)
    private var lastPreview:RawDevelopmentStore.Preview?=null
    private var lastProfile:File?=null
    private val observer:(RawDevelopmentStore.State)->Unit={render(it)}
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window,false)
        val body=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(16),dp(12),dp(16),dp(16)) }
        val scroll=ScrollView(this).apply { isFillViewport=true;addView(body) };setContentView(scroll)
        ViewCompat.setOnApplyWindowInsetsListener(scroll) { v,insets ->
            val bars=insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            val ime=insets.getInsets(WindowInsetsCompat.Type.ime());v.setPadding(bars.left,bars.top,bars.right,maxOf(bars.bottom,ime.bottom));insets
        }
        fun text(value:String,size:Float=15f)=TextView(this).apply { text=value;textSize=size;setPadding(0,dp(6),0,dp(6));body.addView(this) }
        fun button(label:String,action:()->Unit)=Button(this).apply { text=label;minHeight=dp(48);setOnClickListener { action() };body.addView(this,LinearLayout.LayoutParams(-1,-2)) }
        text("RAW development",24f)
        text("Create LogC3 / ARRI Wide Gamut 3 video on this phone. This is an offline reference developer, not live Log recording. Stay on this screen while processing; leaving cancels the task. RAW sources are never overwritten.")
        status=text("Inspecting source…")
        preview=GreySelectionView(this) { roi -> grey=roi;selectionStatus.text="Grey reference in first frame: ${roi.joinToString(", ")} (left, top, width, height)" }
        body.addView(preview,LinearLayout.LayoutParams(-1,dp(240)))
        text("Selection preview only—not calibrated colour. Tap or drag a known, uniformly lit 18% grey patch in the FIRST frame. This does not replace a measured colour-chart calibration.",13f)
        selectionStatus=text("No grey reference selected.")
        coordinateButton=button("Enter grey coordinates") { coordinates() }
        deriveButton=button("Create manufacturer-metadata starting profile") { derive() }
        importButton=button("Import measured / provisional profile") {
            startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE);type="*/*";putExtra(Intent.EXTRA_MIME_TYPES,arrayOf("application/json","text/plain","application/octet-stream"))
            },100)
        }
        savedButton=button("Choose saved profile") {
            val files=store.state.savedProfiles
            AlertDialog.Builder(this).setTitle("Profiles matching this RAW source")
                .setItems(files.map { it.name }.toTypedArray()) { _,i -> store.selectProfile(files[i]) }.setNegativeButton("Close",null).show()
        }
        profileStatus=text("No colour profile selected.")
        profileShare=button("Share selected profile") { store.state.profileFile?.let { share(listOf(it),"application/json") } }
        text("Output size (box reduction in scene-linear colour, never upscaling)")
        scale=Spinner(this);body.addView(scale,LinearLayout.LayoutParams(-1,dp(52)));scale.contentDescription="Output size"
        provisional=CheckBox(this).apply { text="Allow provisional, unmeasured colour profile";body.addView(this) }
        clipping=CheckBox(this).apply { text="Allow final storage-range clipping (counts saved in report)";body.addView(this) }
        text("Output: 10-bit HEVC, video levels, 4:2:0, no audio. Orientation is preserved in the sidecar, not rotated into pixels. The encoder must pass a 10-bit ramp and an 8-bit negative control. A missing route is not replaced by SDR or HLG.",13f)
        exportButton=button("Develop as LogC3") {
            val divisor=divisors.getOrElse(scale.selectedItemPosition){1}
            store.develop(divisor,provisional.isChecked,clipping.isChecked)
        }
        cancelButton=button("Cancel development") { store.cancel() }
        shareButton=button("Share verified video + colour sidecar") { store.state.media?.let { media -> share(listOf(media)+listOfNotNull(store.state.sidecar),"application/octet-stream") } }
        retained=button("Retained exports / partial files") { showRetained() }
        attemptReports=button("Development attempt reports") { showAttemptReports() }
        button("Open clip library") { if(!store.state.busy)startActivity(Intent(this,CaptureLibraryActivity::class.java)) }
        button("Return to camera") { if(store.state.busy)store.cancel();finish() }
        grey=savedInstanceState?.getIntArray("grey")
        val name=intent.getStringExtra("sourceName")
        if(!store.state.busy && name!=null && store.state.index?.file?.name!=name)store.inspect(name)
    }
    override fun onResume(){super.onResume();store.observe(observer)}
    override fun onPause(){store.remove(observer);super.onPause()}
    override fun onStop(){if(!isChangingConfigurations)store.cancel();super.onStop()}
    override fun onSaveInstanceState(out:Bundle){out.putIntArray("grey",grey);super.onSaveInstanceState(out)}
    @Deprecated("Framework callback retained for the existing Activity API")
    override fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?){
        super.onActivityResult(requestCode,resultCode,data)
        if(requestCode==100 && resultCode==RESULT_OK)data?.data?.let(store::importProfile)
    }
    private fun render(state:RawDevelopmentStore.State) {
        status.text=state.message
        if(state.busy)window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        if(lastPreview!==state.preview){lastPreview=state.preview;preview.setPreview(state.preview);grey?.let(preview::setSelection)}
        if(lastProfile!=state.profileFile) {
            lastProfile=state.profileFile
            state.profile?.let { p ->
                divisors=listOf(1,2,4).filter { p.crop[2]%(2*it)==0 && p.crop[3]%(2*it)==0 }
                scale.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,divisors.map { d -> "${p.crop[2]/d} × ${p.crop[3]/d} · ${if(d==1)"full crop" else "1/$d linear reduction"}" })
                scale.setSelection(divisors.indexOf(2).takeIf { it>=0 } ?: 0)
                // Loading a provisional profile is not consent to use it for export.
                provisional.isChecked=false
            }
        }
        profileStatus.text=state.profile?.let { p ->
            "${p.status.uppercase()} profile\n${p.json.getJSONObject("calibration").getString("illuminant")}\nCrop: ${p.crop.joinToString()}\nImported 'measured' is a supplied assertion, not app certification."
        } ?: "No colour profile selected. Legacy sources without metadata snapshots require an imported profile."
        val ready=state.index!=null && !state.busy
        importButton.isEnabled=ready;savedButton.isEnabled=ready && state.savedProfiles.isNotEmpty()
        deriveButton.isEnabled=ready && state.index?.header?.optJSONObject("rawCalibration")!=null
        coordinateButton.isEnabled=ready;preview.isEnabled=ready
        exportButton.isEnabled=ready && state.profile!=null;scale.isEnabled=exportButton.isEnabled
        clipping.isEnabled=!state.busy;provisional.isEnabled=!state.busy
        attemptReports.isEnabled=!state.busy
        cancelButton.isEnabled=state.busy;shareButton.isEnabled=!state.busy && state.media?.isFile==true
        profileShare.isEnabled=!state.busy && state.profileFile?.isFile==true;retained.isEnabled=!state.busy
    }
    private fun coordinates() {
        val layout=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(16),0,dp(16),0) }
        val names=listOf("Left (even)","Top (even)","Width (even)","Height (even)")
        val fields=names.mapIndexed { i,n -> EditText(this).apply { hint=n;contentDescription=n;inputType=InputType.TYPE_CLASS_NUMBER;grey?.let { setText(it[i].toString()) };layout.addView(this) } }
        val dialog=AlertDialog.Builder(this).setTitle("18% grey patch in RAW coordinates").setView(layout).setNegativeButton("Cancel",null).setPositiveButton("Use",null).create()
        dialog.setOnShowListener { dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            runCatching { val r=fields.map { it.text.toString().toInt() }.toIntArray();val index=requireNotNull(store.state.index)
                require(r.all { it>=0 && it%2==0 } && r[2]>=4 && r[3]>=4 && r[0].toLong()+r[2]<=index.width && r[1].toLong()+r[3]<=index.height)
                grey=r;preview.setSelection(r);dialog.dismiss()
            }.onFailure { fields[0].error="Use even coordinates inside the RAW image; minimum patch 4 × 4." }
        } };dialog.show()
    }
    private fun derive() {
        val roi=grey ?: run { coordinates();return }
        val snapshot=store.state.index?.header?.optJSONObject("rawCalibration") ?: return
        val endpoints=listOf(1,2).filter { !snapshot.isNull("forwardMatrix$it") && !snapshot.isNull("calibrationTransform$it") && !snapshot.isNull("referenceIlluminant$it") }
        if(endpoints.isEmpty()){AlertDialog.Builder(this).setMessage("Captured metadata does not include a usable forward + calibration matrix pair. Import a measured profile instead.").setPositiveButton("Close",null).show();return}
        AlertDialog.Builder(this).setTitle("Select the matching reference illuminant")
            .setItems(endpoints.map { "Reference $it · Camera2 illuminant code ${snapshot.optInt("referenceIlluminant$it")}" }.toTypedArray()) { _,i ->
                AlertDialog.Builder(this).setTitle("Create a provisional starting profile?")
                    .setMessage("Confirm that the selected rectangle is a uniformly lit 18% grey reference in frame one, and the selected illuminant matches the shot. This uses manufacturer matrices and a grey normalization, not a measured colour-chart fit. No automatic illuminant interpolation or dynamic-range equivalence is claimed.")
                    .setNegativeButton("Cancel",null).setPositiveButton("Create provisional profile") { _,_ -> store.deriveProfile(endpoints[i],roi.copyOf()) }.show()
            }.setNegativeButton("Cancel",null).show()
    }
    private fun showAttemptReports() {
        val files=store.evidenceDirectory.listFiles().orEmpty().filter { it.isFile && it.name.matches(Regex("attempt-[0-9a-f-]+\\.json")) && it.length()>0 }
            .sortedByDescending { it.lastModified() }
        if(files.isEmpty()) {
            AlertDialog.Builder(this).setMessage("No attempt reports retained. After development, reports show each observed stage, including unavailable or failed routes. They do not certify a physical camera.").setPositiveButton("Close",null).show();return
        }
        AlertDialog.Builder(this).setTitle("Attempt reports · not camera certification").setItems(files.map { it.name }.toTypedArray()) { _,i -> share(listOf(files[i]),"application/json") }
            .setNegativeButton("Close",null).show()
    }
    private fun showRetained() {
        val files=store.outputDirectory.listFiles().orEmpty().filter { it.isFile && it.name.matches(Regex("logc3-[0-9a-f-]+(\\.partial)?\\.mp4")) }.sortedByDescending { it.lastModified() }
        if(files.isEmpty()){AlertDialog.Builder(this).setMessage("No retained exports. A failed encoder qualification does not modify RAW sources.").setPositiveButton("Close",null).show();return}
        AlertDialog.Builder(this).setTitle("Exports / unverified partial files").setItems(files.map { "${if(it.name.contains(".partial."))"UNVERIFIED PARTIAL · " else ""}${it.name}" }.toTypedArray()) { _,i ->
            val f=files[i];val sidecar=File(f.parentFile,f.name+".logc3.json")
            AlertDialog.Builder(this).setTitle(f.name).setMessage(if(f.name.contains(".partial."))"This file did not complete verification; it may be incomplete. The original RAW remains unchanged." else "Import as ARRI Wide Gamut 3 / LogC3 with video levels and the sidecar's orientation. Generic playback is not colour-correct.")
                .setPositiveButton("Share") { _,_ -> share(listOf(f)+listOfNotNull(sidecar.takeIf { it.isFile }),"application/octet-stream") }
                .setNeutralButton("Keep",null).setNegativeButton("Delete…") { _,_ ->
                    AlertDialog.Builder(this).setMessage("Permanently delete this export and its sidecar? RAW sources are not deleted.").setNegativeButton("Keep",null)
                        .setPositiveButton("Delete") { _,_ -> if(f.delete())sidecar.delete() else Toast.makeText(this,"Export could not be deleted",Toast.LENGTH_LONG).show() }.show()
                }.show()
        }.setNegativeButton("Close",null).show()
    }
    private fun share(files:List<File>,mime:String) {
        runCatching {
            val uris=files.map { FileProvider.getUriForFile(this,"$packageName.files",it) }
            val intent=Intent(Intent.ACTION_SEND_MULTIPLE).apply { type=mime;putParcelableArrayListExtra(Intent.EXTRA_STREAM,ArrayList(uris));addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                clipData=ClipData.newUri(contentResolver,"RAW development",uris.first()).also { c -> uris.drop(1).forEach { c.addItem(ClipData.Item(it)) } } }
            startActivity(Intent.createChooser(intent,"Share RAW development"))
        }.onFailure { Toast.makeText(this,"Share failed: ${it.message}",Toast.LENGTH_LONG).show() }
    }
    private fun dp(value:Int)=(value*resources.displayMetrics.density).roundToInt()
}

private class GreySelectionView(context:android.content.Context,private val selected:(IntArray)->Unit):View(context) {
    private var bitmap:Bitmap?=null;private var rawWidth=0;private var rawHeight=0
    private var roi:IntArray?=null;private val target=RectF();private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
    private var startX=0f;private var startY=0f
    init { contentDescription="Uncalibrated RAW reference preview. Tap or drag a grey patch; coordinate entry is also available.";isFocusable=true;minimumHeight=160 }
    fun setPreview(value:RawDevelopmentStore.Preview?) {
        bitmap?.recycle();bitmap=value?.let { Bitmap.createBitmap(it.argb,it.width,it.height,Bitmap.Config.ARGB_8888) }
        rawWidth=value?.rawWidth ?: 0;rawHeight=value?.rawHeight ?: 0;roi=null;invalidate()
    }
    fun setSelection(value:IntArray){roi=value.copyOf();selected(value.copyOf());invalidate()}
    override fun onDraw(canvas:Canvas) {
        super.onDraw(canvas);val image=bitmap ?: return
        val s=minOf(width.toFloat()/image.width,height.toFloat()/image.height)
        val w=image.width*s;val h=image.height*s;target.set((width-w)/2,(height-h)/2,(width+w)/2,(height+h)/2)
        paint.style=Paint.Style.FILL;canvas.drawBitmap(image,null,target,paint)
        roi?.let { r -> paint.color=0xff72e5d1.toInt();paint.strokeWidth=3f;paint.style=Paint.Style.STROKE
            canvas.drawRect(target.left+r[0]*target.width()/rawWidth,target.top+r[1]*target.height()/rawHeight,
                target.left+(r[0]+r[2])*target.width()/rawWidth,target.top+(r[1]+r[3])*target.height()/rawHeight,paint) }
    }
    override fun performClick():Boolean{super.performClick();return true}
    override fun onTouchEvent(event:MotionEvent):Boolean {
        if(!isEnabled || bitmap==null || target.isEmpty)return false
        when(event.actionMasked) {
            MotionEvent.ACTION_DOWN->{if(!target.contains(event.x,event.y))return false;startX=event.x;startY=event.y;parent.requestDisallowInterceptTouchEvent(true);return true}
            MotionEvent.ACTION_MOVE,MotionEvent.ACTION_UP->{
                fun rx(x:Float)=(((x-target.left)/target.width()*rawWidth).toInt().coerceIn(0,rawWidth) and -2)
                fun ry(y:Float)=(((y-target.top)/target.height()*rawHeight).toInt().coerceIn(0,rawHeight) and -2)
                var left=minOf(rx(startX),rx(event.x));var top=minOf(ry(startY),ry(event.y))
                var right=maxOf(rx(startX),rx(event.x));var bottom=maxOf(ry(startY),ry(event.y))
                if(right-left<4){val n=minOf(16,rawWidth);left=(left-n/2).coerceIn(0,rawWidth-n);right=left+n}
                if(bottom-top<4){val n=minOf(16,rawHeight);top=(top-n/2).coerceIn(0,rawHeight-n);bottom=top+n}
                setSelection(intArrayOf(left,top,right-left,bottom-top))
                if(event.actionMasked==MotionEvent.ACTION_UP){parent.requestDisallowInterceptTouchEvent(false);performClick()};return true
            }
            MotionEvent.ACTION_CANCEL->{parent.requestDisallowInterceptTouchEvent(false);return true}
        }
        return super.onTouchEvent(event)
    }
}
