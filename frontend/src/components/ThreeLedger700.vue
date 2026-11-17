<script setup>
// SOS_CHARTS_701
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
const props = defineProps({series:{type:Array,default:()=>[]},currency:{type:String,default:'BDT'},delivery:{type:Object,default:null}})
const mode=ref('bars'), metric=ref('net'), surface=ref(null), active=ref(-1), supported=ref(false)
const modes=[['bars','Revenue bars'],['trend','Trend ribbon'],['delivery','Delivery ring']]
const colors=['#946d4b','#c69d70','#d8cbbd']
const num=v=>Number.isFinite(Number(v))?Number(v):0
const rows=computed(()=>mode.value==='delivery'?(props.delivery?.visible ? [
 {label:'Ready for handover',value:num(props.delivery.ready)},
 {label:'Delivered',value:num(props.delivery.delivered)},
 {label:'Other statuses',value:Math.max(0,num(props.delivery.scanned)-num(props.delivery.ready)-num(props.delivery.delivered))}]:[]):props.series.slice(-14).map(r=>({label:String(r.date),value:num(r[metric.value])})))
const money=computed(()=>mode.value!=='delivery' && metric.value!=='invoice_count')
const format=v=>(money.value?props.currency+' ':'')+num(v).toLocaleString('en-BD',{maximumFractionDigits:money.value?2:0})
const total=computed(()=>rows.value.reduce((s,r)=>s+r.value,0))
const picked=computed(()=>rows.value[active.value])
const max=computed(()=>Math.max(1,...rows.value.map(r=>Math.abs(r.value))))
let cleanup=()=>{}, generation=0, mounted=false
async function draw(){
 const token=++generation;cleanup();supported.value=false;active.value=-1
 if(!mounted||!surface.value||!rows.value.length)return
 let renderer,scene,observer,frame=0,disposed=false
 const handlers=[]
 const listen=(el,event,fn)=>{el.addEventListener(event,fn);handlers.push(()=>el.removeEventListener(event,fn))}
 const dispose=()=>{disposed=true;cancelAnimationFrame(frame);observer?.disconnect();handlers.forEach(fn=>fn());scene?.traverse(o=>{o.geometry?.dispose();if(o.material)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>m.dispose())});renderer?.dispose();renderer?.domElement.remove()}
 cleanup=dispose
 try{
 const T=await import('three');if(disposed||token!==generation)return
 scene=new T.Scene()
 renderer=new T.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'})
 renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.75));renderer.outputColorSpace=T.SRGBColorSpace
 surface.value.appendChild(renderer.domElement)
 const camera=new T.OrthographicCamera(-10,10,7,-7,.1,100)
 camera.position.set(0,10,22);camera.lookAt(0,0,0)
 scene.add(new T.AmbientLight(0xffffff,2.2))
 const light=new T.DirectionalLight(0xffeedb,3);light.position.set(-5,12,10);scene.add(light)
 const group=new T.Group();scene.add(group);const hits=[]
 const material=color=>new T.MeshStandardMaterial({color,roughness:.35,metalness:.18})
 const add=(geometry,color,index)=>{const mesh=new T.Mesh(geometry,material(color));group.add(mesh);if(index!==undefined){mesh.userData.index=index;hits.push(mesh)}return mesh}
 const records=rows.value
 if(mode.value==='delivery'){
   const sum=total.value;let start=0
   records.forEach((r,i)=>{if(r.value<=0||sum<=0)return;const angle=r.value/sum*Math.PI*2
     const shape=new T.Shape();shape.absarc(0,0,4,start,start+angle,false);shape.absarc(0,0,2.65,start+angle,start,true);shape.closePath()
     const mesh=add(new T.ExtrudeGeometry(shape,{depth:.65,bevelEnabled:true,bevelSegments:2,steps:1,bevelSize:.04,bevelThickness:.04,curveSegments:64}),colors[i],i)
     mesh.rotation.x=-.65;start+=angle
   })
 }else{
   const gap=16/Math.max(records.length,1),points=[]
   const floor=new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(-8.8,0,0),new T.Vector3(8.8,0,0)]),new T.LineBasicMaterial({color:0xb9a18b}));group.add(floor)
   records.forEach((r,i)=>{const x=(i-(records.length-1)/2)*gap,y=r.value/max.value*4.7;points.push(new T.Vector3(x,y,.1))
    if(mode.value==='bars'){
     if(r.value!==0){const b=add(new T.BoxGeometry(gap*.58,Math.abs(y),.7),r.value<0?'#a66559':'#946d4b',i);b.position.set(x,y/2,0)}
    }else{const dot=add(new T.SphereGeometry(.12,16,12),r.value<0?'#a66559':'#946d4b',i);dot.position.set(x,y,.1)}
   })
   if(mode.value==='trend'&&points.length>1){
    group.add(new T.Line(new T.BufferGeometry().setFromPoints(points),new T.LineBasicMaterial({color:0x715036})))
    for(let i=1;i<points.length;i++){
      const a=points[i-1],b=points[i];const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute([a.x,0,0,a.x,a.y,0,b.x,b.y,0,a.x,0,0,b.x,b.y,0,b.x,0,0],3));g.computeVertexNormals()
      group.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0xc69d70,transparent:true,opacity:.32,side:T.DoubleSide})))
    }
   }
 }
 const render=()=>{if(!disposed&&!document.hidden)renderer.render(scene,camera)}
 const resize=()=>{if(disposed||!surface.value)return;const w=surface.value.clientWidth,h=surface.value.clientHeight;const aspect=Math.max(w,1)/Math.max(h,1),halfH=Math.max(7,10/aspect);camera.left=-halfH*aspect;camera.right=halfH*aspect;camera.top=halfH;camera.bottom=-halfH;camera.updateProjectionMatrix();renderer.setSize(w,h,false);render()}
 observer=new ResizeObserver(resize);observer.observe(surface.value)
 const ray=new T.Raycaster(),pointer=new T.Vector2()
 listen(renderer.domElement,'pointermove',e=>{const rect=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);ray.setFromCamera(pointer,camera);active.value=ray.intersectObjects(hits)[0]?.object.userData.index??-1;hits.forEach(m=>m.material.emissive.set(m.userData.index===active.value?0x25180f:0));render()})
 listen(renderer.domElement,'pointerleave',()=>{active.value=-1;hits.forEach(m=>m.material.emissive.set(0));render()})
 listen(renderer.domElement,'webglcontextlost',e=>{e.preventDefault();dispose();supported.value=false})
 listen(document,'visibilitychange',render)
 supported.value=true;resize()
 if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches){const start=performance.now();const animate=now=>{if(disposed)return;const t=Math.min(1,(now-start)/650);group.scale.y=.2+.8*(1-Math.pow(1-t,3));render();if(t<1)frame=requestAnimationFrame(animate)};frame=requestAnimationFrame(animate)}
 }catch(e){dispose();supported.value=false}
}
onMounted(()=>{mounted=true;draw()})
watch([rows,mode],draw,{deep:true,flush:'post'})
onBeforeUnmount(()=>{mounted=false;++generation;cleanup()})
</script>
<template>
 <section class="atelier">
  <div class="toolbar"><div class="switch"><button v-for="[key,label] in modes" :key="key" :aria-pressed="mode===key" :class="{chosen:mode===key}" @click="mode=key" type="button">{{label}}</button></div>
   <select v-if="mode!=='delivery'" v-model="metric" aria-label="Chart metric"><option value="net">Net revenue</option><option value="gross">Gross invoiced</option><option value="invoice_count">Invoice count</option></select>
  </div>
  <div class="stage">
   <div class="headline"><span>{{picked?.label || (mode==='delivery'?'RECENT JOB SAMPLE':'DISPLAYED 14-DAY WINDOW')}}</span><strong>{{format(picked?.value ?? total)}}</strong><small>{{picked?'Selected value':mode==='delivery'?'Jobs inspected':'Total · selected metric'}}</small></div>
   <div ref="surface" class="canvas" aria-hidden="true"></div>
   <div v-if="!supported" class="fallback"><p>{{rows.length?'Chart values are available below.':'No accessible data available.'}}</p></div>
   <div class="legend"><span><i></i>{{mode==='delivery'?'Ready · Delivered · Other':'Bronze: positive · Rose: negative'}}</span><span>{{supported?'Interactive 3D':'Data view'}}</span></div>
  </div>
  <p class="scope">{{mode==='delivery'?'Up to 200 recently modified authorized jobs. Independent of invoice date filters.':'Last 14 days of selected period · submitted invoices including signed returns · zero baseline.'}}</p>
  <div class="values" :class="{compact:mode==='delivery'}" aria-label="Exact chart values">
    <button v-for="(r,i) in rows" :key="r.label" type="button" @focus="active=i" @blur="active=-1" @mouseenter="active=i" @mouseleave="active=-1" :class="{selected:active===i}"><span>{{r.label}}</span><strong>{{format(r.value)}}</strong><i :style="{width:Math.abs(r.value)/max*100+'%',background:r.value<0?'#a66559':colors[i%3]}"></i></button>
  </div>
 </section>
</template>
<style scoped>
.atelier{color:#493426;font-variant-numeric:tabular-nums}.toolbar{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:12px}.switch{display:flex;padding:4px;background:#eee4d9;border-radius:11px;gap:3px}.switch button,select{font:inherit;font-size:11px;border:0;border-radius:8px;padding:8px 10px;color:#765f4b;background:transparent;cursor:pointer}.switch .chosen{background:#614532;color:#fff9f0;box-shadow:0 3px 8px #533b2920}select{border:1px solid #e0d2c3;background:#fffaf3;max-width:100%}.stage{height:330px;position:relative;overflow:hidden;border-radius:16px;border:1px solid #e3d4c4;background:radial-gradient(ellipse at 55% 30%,#fffaf1,#eee1d2)}.canvas{position:absolute;inset:0}.canvas :deep(canvas){width:100%;height:100%;display:block}.headline{position:absolute;left:20px;top:18px;z-index:1;display:grid;gap:5px;pointer-events:none}.headline span{font-size:9px;letter-spacing:.12em;color:#91755d}.headline strong{font-size:27px;letter-spacing:-.04em}.headline small{font-size:10px;color:#9c8571}.legend{position:absolute;bottom:14px;left:18px;right:18px;display:flex;justify-content:space-between;font-size:9px;gap:8px;color:#856b55;pointer-events:none}.legend i{display:inline-block;width:6px;height:6px;background:#946d4b;border-radius:50%;margin-right:5px}.scope{font-size:10px!important;line-height:1.5;margin:10px 0!important;color:#947c67!important}.values{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px}.values button{position:relative;overflow:hidden;display:grid;gap:5px;text-align:left;padding:8px 6px 11px;border:1px solid #eaded1;background:#fcf8f2;border-radius:7px;color:inherit;min-width:0;cursor:pointer}.values span{font-size:8px;color:#967e68}.values strong{font-size:9px;overflow-wrap:anywhere}.values i{position:absolute;bottom:0;left:0;height:3px}.values .selected{background:#efe0cf;border-color:#ac815d}.values.compact{grid-template-columns:repeat(3,minmax(0,1fr))}.fallback{position:absolute;top:60%;width:100%;text-align:center;font-size:12px;color:#957a64}button:focus-visible,select:focus-visible{outline:2px solid #926641;outline-offset:2px}@media(max-width:600px){.values{grid-template-columns:repeat(4,minmax(0,1fr))}.stage{height:290px}.switch button{font-size:10px;padding:8px}.headline strong{font-size:22px}}
</style>
