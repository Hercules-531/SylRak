import {useState, type FormEvent} from 'react';
import {Link} from 'react-router-dom';
import {ArrowUpRight, Plus, Sticker} from 'lucide-react';
import {post, patch, useGet, time, date, type Observation} from './api';
import {Badge, ErrorState, Loading, Modal, useAction} from './ui';

// Mirrors backend/marks.py: 1080p lane camera, 1.7 m car across ~500 px.
const MM_PER_PIXEL=3.4;
const DETECT:Record<string,{label:string;tone:string}>={
 'reliable':{label:'Reliable',tone:'green'},'mostly':{label:'Mostly detectable',tone:'green'},
 'angle-dependent':{label:'From the right angle',tone:'neutral'},'glare-limited':{label:'Sometimes · glare',tone:'amber'},
 'close-up only':{label:'Close-up only',tone:'red'},'unknown':{label:'Size not recorded',tone:'neutral'}};
const FEASIBILITY=[
 {band:'reliable',feature:'Large decals, wraps, colored panels',size:'30 cm+',px:'100+ px',verdict:'Yes, reliable'},
 {band:'angle-dependent',feature:'Stickers (windshield or bumper)',size:'~10 cm',px:'~30 px',verdict:'Yes, from the right angle'},
 {band:'mostly',feature:'Broken tail light, missing bumper, big dent',size:'20 cm+',px:'50+ px',verdict:'Mostly yes; dents are hard in flat lighting'},
 {band:'glare-limited',feature:'Cracked or shattered windshield',size:'Large crack',px:'Visible',verdict:'Sometimes; reflections interfere'},
 {band:'close-up only',feature:'Small windshield chip',size:'~1 cm',px:'~3 px',verdict:'Not from a traffic camera; needs a close-up'}];

function detectability(category:string,size:number|null){
 if(size==null)return 'unknown';if(size<8)return 'close-up only';if(category==='glass damage')return 'glare-limited';
 return size>=30?'reliable':size>=20?'mostly':'angle-dependent';
}
export function DetectBadge({value}:{value:string}){const d=DETECT[value]||DETECT.unknown;return <Badge tone={d.tone}>{d.label}</Badge>}
const sizeText=(m:any)=>m.size_cm!=null?`~${m.size_cm} cm · ~${m.pixels} px`:'Size not recorded';
const statusTone=(s:string)=>s==='confirmed'?'green':s==='suggested'?'amber':'neutral';

function ReviewMark({mark,onClose}:{mark:any;onClose:()=>void}){
 const [reason,setReason]=useState(''),action=useAction();
 const save=async(status:string)=>{if(await action(()=>patch('/marks/'+mark.id,{status,reason}),'Feature review saved'))onClose()};
 return <Modal open title="Review logged feature" onClose={onClose}><p><strong>{mark.label}</strong> · {mark.part} · {mark.origin}</p>
  <label>Reason<textarea aria-label="Feature review reason" value={reason} onChange={e=>setReason(e.target.value)} placeholder="What you checked in the image"/></label>
  <div className="button-row">{mark.status!=='confirmed'&&<button className="primary" disabled={reason.trim().length<5} onClick={()=>save('confirmed')}>Confirm feature</button>}{mark.status!=='rejected'&&<button className="secondary" disabled={reason.trim().length<5} onClick={()=>save('rejected')}>Reject</button>}</div>
  {!!mark.history?.length&&<details><summary>History ({mark.history.length})</summary>{mark.history.map((h:any,i:number)=><p key={i}>{h.action} · {h.actor} · {date(h.at)} {time(h.at)}{h.reason?' — '+h.reason:''}</p>)}</details>}</Modal>
}

export function LogMarkForm({observation,onDone}:{observation:Observation;onDone:()=>void}){
 const tax=useGet<any>('/marks/taxonomy'),action=useAction();
 const [form,setForm]=useState({category:'sticker',part:'windshield',label:'',size:'',notes:'',origin:'operator log'});
 const size=form.size===''?null:Number(form.size),band=detectability(form.category,size);
 const submit=async(e:FormEvent)=>{e.preventDefault();
  const saved=await action(()=>post('/observations/'+observation.id+'/marks',{category:form.category,part:form.part,label:form.label,size_cm:size,notes:form.notes,origin:form.origin}),'Feature logged and indexed');
  if(saved)onDone()};
 if(!tax.data)return <Loading/>;
 return <form className="mark-form" onSubmit={submit}>
  <div className="filter-grid mark-form-grid">
   <label>Feature type<select value={form.category} onChange={e=>setForm({...form,category:e.target.value})}>{tax.data.categories.map((c:string)=><option key={c}>{c}</option>)}</select></label>
   <label>Location on vehicle<select value={form.part} onChange={e=>setForm({...form,part:e.target.value})}>{tax.data.parts.map((p:string)=><option key={p}>{p}</option>)}</select></label>
   <label className="mark-form-wide">Description<input aria-label="Feature description" value={form.label} onChange={e=>setForm({...form,label:e.target.value})} placeholder="e.g. Ganesh sticker, top-left of rear glass" minLength={3} maxLength={100} required/></label>
   <label>Approx. size · cm<input type="number" min={0.5} max={500} step={0.5} value={form.size} onChange={e=>setForm({...form,size:e.target.value})} placeholder="10"/></label>
   <label>Source<select value={form.origin} onChange={e=>setForm({...form,origin:e.target.value})}><option value="operator log">Operator log</option><option value="model suggestion">Model suggestion (demo)</option></select></label>
   <label className="mark-form-wide">Notes<input value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} maxLength={500} placeholder="Optional: color, shape, what makes it distinctive"/></label>
  </div>
  <div className="detect-preview"><span>At a 1080p lane camera</span><strong className="mono">{size!=null&&size>0?`~${size} cm ≈ ${Math.round(size*10/MM_PER_PIXEL)} px`:'Add a size to estimate'}</strong><DetectBadge value={band}/>{form.origin==='model suggestion'&&<Badge tone="amber">Saved as a suggestion until confirmed</Badge>}</div>
  <div className="button-row"><button type="button" className="secondary" onClick={onDone}>Cancel</button><button className="primary" disabled={form.label.trim().length<3}><Plus size={16}/>Log feature</button></div>
 </form>
}

function MarkList({marks,showSighting=false}:{marks:any[];showSighting?:boolean}){
 const [review,setReview]=useState<any>(null);
 return <><ul className="mark-list">{marks.map(m=><li key={m.id} className={'mark-item '+m.status}>
  <div className="mark-main"><span className="mark-category">{m.category}</span><strong>{m.label}</strong><span className="muted">{m.part} · {sizeText(m)}</span>
   {showSighting&&m.observation?.camera&&<span className="muted">{m.observation.camera_id} · {m.observation.camera.name} · {time(m.observation.observed_at,true)} IST</span>}{m.notes&&<small className="muted">{m.notes}</small>}</div>
  <div className="mark-side"><DetectBadge value={m.detectability}/><Badge tone={statusTone(m.status)}>{m.status}</Badge><small className="muted">{m.origin}</small><button className="text-button" onClick={()=>setReview(m)}>Review</button></div>
 </li>)}</ul>{review&&<ReviewMark mark={review} onClose={()=>setReview(null)}/>}</>
}

export function SightingMarks({observation}:{observation:Observation}){
 const q=useGet<any[]>('/observations/'+observation.id+'/marks'),[adding,setAdding]=useState(false);
 return <section className="sighting-marks"><div className="section-intro"><div><div className="eyebrow">LOGGED FEATURES</div><p>Stickers, glass damage and broken parts seen on this sighting. Indexed for search across cameras.</p></div>{!adding&&<button className="secondary" onClick={()=>setAdding(true)}><Plus size={15}/>Log a feature</button>}</div>
  {adding&&<LogMarkForm observation={observation} onDone={()=>setAdding(false)}/>}
  {q.data?(q.data.length?<MarkList marks={q.data}/>:!adding&&<p className="muted">No features logged on this sighting.</p>):<Loading/>}</section>
}

export function VehicleMarks({vehicleId,current}:{vehicleId:string;current?:Observation}){
 const q=useGet<any[]>('/vehicles/'+vehicleId+'/marks'),[adding,setAdding]=useState(false);
 const active=q.data?.filter(m=>m.status!=='rejected')||[];
 return <section className="panel vehicle-marks"><div className="panel-heading"><h2><Sticker size={16}/>Logged features <span className="panel-counter">{active.length}</span></h2>
  <div className="panel-right"><Link className="text-button" to="/investigations?mode=description">Search by feature <ArrowUpRight size={14}/></Link>{current&&!adding&&<button className="secondary" onClick={()=>setAdding(true)}><Plus size={15}/>Log on selected sighting</button>}</div></div>
  <div className="vehicle-marks-body">{adding&&current&&<><p className="muted">Logging on {current.camera_id} · {current.camera.name} · {time(current.observed_at,true)} IST</p><LogMarkForm observation={current} onDone={()=>setAdding(false)}/></>}
  {q.isError?<ErrorState error={q.error as Error}/>:!q.data?<Loading/>:q.data.length?<MarkList marks={q.data} showSighting/>:!adding&&<p className="muted">No stickers, damage or broken parts logged for this vehicle yet.</p>}</div></section>
}

type FeatureValue={feature_type:string;feature_part:string;feature:string};
// Visible-feature filters for Investigations → Vehicle description, backed by the indexed vehicle_marks table.
export function FeatureFilters({value,onChange}:{value:FeatureValue;onChange:(patch:Partial<FeatureValue>,apply?:boolean)=>void}){
 const tax=useGet<any>('/marks/taxonomy'),index=useGet<any>('/marks/index?run_id=current');const i=index.data;
 return <div className="feature-filters">
  <div className="feature-filters-heading"><span className="eyebrow">VISIBLE FEATURES</span><p>Stickers, glass damage and broken parts logged on sightings.{i?` ${i.total} indexed across ${i.vehicles} plated vehicles and ${i.unidentified_sightings} unplated sightings.`:''}</p></div>
  <div className="facet-row" role="group" aria-label="Feature type"><button type="button" className="facet-chip" aria-pressed={!value.feature_type} onClick={()=>onChange({feature_type:''},true)}>Any feature</button>
   {tax.data?.categories.filter((c:string)=>i?.category?.[c]).map((c:string)=><button type="button" key={c} className="facet-chip" aria-pressed={value.feature_type===c} onClick={()=>onChange({feature_type:value.feature_type===c?'':c},true)}>{c} <span>{i.category[c]}</span></button>)}</div>
  <div className="feature-filter-fields">
   <label>Location on vehicle<select aria-label="Feature location" value={value.feature_part} onChange={e=>onChange({feature_part:e.target.value})}><option value="">Any location</option>{tax.data?.parts.map((p:string)=><option key={p} value={p}>{p}{i?.part?.[p]?` (${i.part[p]})`:''}</option>)}</select></label>
   <label>Feature description<input aria-label="Feature description search" value={value.feature} onChange={e=>onChange({feature:e.target.value})} placeholder="e.g. Ganesh sticker, cracked tail light"/></label>
  </div>
  <details className="feasibility-guide"><summary>Camera feasibility guide</summary>
   <p className="muted">Assumes a 1080p camera covering one lane, where a car is about 500 px wide (≈3.4 mm per pixel).</p>
   <div className="table-scroll"><table className="data-table"><thead><tr><th>Feature</th><th>Real size</th><th>Pixels on a traffic camera</th><th>Feasible?</th><th>Indexed</th></tr></thead><tbody>
    {FEASIBILITY.map(r=><tr key={r.band}><td className="wrap-cell">{r.feature}</td><td>{r.size}</td><td className="mono">{r.px}</td><td className="wrap-cell"><DetectBadge value={r.band}/> {r.verdict}</td><td>{i?.detectability?.[r.band]||0}</td></tr>)}
   </tbody></table></div></details>
 </div>
}

