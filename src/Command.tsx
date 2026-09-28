import {useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {Link} from 'react-router-dom';
import {ArrowDown,ArrowUpRight,ArrowLeft,ArrowRight,ScanLine,ShieldAlert,X} from 'lucide-react';
import {date,number,time,useGet,type Alert,type Camera,type Observation,type Snapshot} from './api';
import {Empty,ErrorState,Loading,Plate} from './ui';
import MapView from './MapView';
import {goToSection,useScrollScene} from './sceneMotion';

const noObservations:Observation[]=[];

function CameraDiagram({cameras}:{cameras:Camera[]}){
 const xs=cameras.map(c=>c.lon),ys=cameras.map(c=>c.lat);
 const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
 return <svg className="network-diagram" viewBox="0 0 620 310" role="img" aria-label="Camera availability at simulated Delhi locations">
  <path d="M28 78H592M28 155H592M28 232H592M155 28V282M310 28V282M465 28V282" className="diagram-grid"/>
  {cameras.map(c=>{const x=55+(c.lon-minX)/(maxX-minX||1)*510,y=45+(maxY-c.lat)/(maxY-minY||1)*210;return <g key={c.id} className={'diagram-camera '+c.status}><title>{c.id+' '+c.name+' · '+c.status}</title><circle cx={x} cy={y} r="15"/><circle cx={x} cy={y} r="3"/><text x={x+22} y={y+4}>{c.id}</text></g>})}
 </svg>;
}

export default function Command({snapshot,toolbar,today,onEvidence,onAlert,onRecognize}:{snapshot:Snapshot;toolbar:ReactNode;today:string;onEvidence:(o:Observation)=>void;onAlert:(a:Alert)=>void;onRecognize:()=>void}){
 const hero=useRef<HTMLElement>(null),heroCopy=useRef<HTMLDivElement>(null),heroShade=useRef<HTMLDivElement>(null),networkNote=useRef<HTMLDivElement>(null);
 const journey=useRef<HTMLElement>(null);
 const [selectedCamera,setSelectedCamera]=useState<string>();
 const [activeStop,setActiveStop]=useState(0),[subject,setSubject]=useState<'coverage'|'passages'|'alerts'>('coverage');
 const lastStep=useRef(-1);
 const seed=useGet<any>('/observations?plate=DL4CAB6672&run_id=current&limit=1');
 const target=useGet<Observation>('/observations/'+snapshot.run.target_observation_id,!!snapshot.run.target_observation_id);
 const lead=target.data?.vehicle_id?target.data:seed.data?.items?.[0];
 const vehicle=useGet<any>('/vehicles/'+lead?.vehicle_id+'?run_id='+lead?.run_id,!!lead?.vehicle_id);
 const traffic=useGet<any>('/traffic');
 const observations=useMemo<Observation[]>(()=>vehicle.data?.observations?.filter((o:Observation)=>o.status==='accepted').sort((a:Observation,b:Observation)=>a.observed_at-b.observed_at)||noObservations,[vehicle.data]);
 const stop=observations[Math.min(activeStop,Math.max(0,observations.length-1))];
 const selected=snapshot.cameras.find(c=>c.id===selectedCamera);
 const online=snapshot.cameras.filter(c=>c.status==='online').length;
 const vehicleUrl=lead?.vehicle_id?'/vehicles/'+lead.vehicle_id+'?run='+lead.run_id:'/investigations';
 useEffect(()=>{setActiveStop(0);lastStep.current=-1},[lead?.vehicle_id,lead?.run_id]);
 useScrollScene(hero,(p,reduced)=>{
  if(heroCopy.current){heroCopy.current.style.opacity=String(reduced?1:Math.max(0,1-p*2.8));heroCopy.current.style.transform=reduced?'none':`translateY(${-p*100}px)`;heroCopy.current.style.visibility=!reduced&&p>.5?'hidden':'visible'}
  if(heroShade.current)heroShade.current.style.opacity=String(reduced?.75:Math.max(.04,.82-p*1.35));
  if(networkNote.current){networkNote.current.style.opacity=String(reduced?0:Math.max(0,Math.min(1,(p-.4)*4)));networkNote.current.style.visibility=!reduced&&p>.4?'visible':'hidden'}
 });
 useScrollScene(journey,(p,reduced)=>{
  if(reduced||innerWidth<900||!observations.length)return;
  const next=Math.min(observations.length-1,Math.floor(p*observations.length));
  if(next!==lastStep.current){lastStep.current=next;setActiveStop(next)}
 });
 const step=(index:number)=>setActiveStop(Math.max(0,Math.min(observations.length-1,index)));
 const priorities:Record<string,number>={critical:0,high:1,medium:2};
 const topAlert=[...snapshot.alerts].sort((a,b)=>(priorities[a.priority]??3)-(priorities[b.priority]??3)||b.updated_at-a.updated_at)[0];
 const selectedPlate=lead?.plate||snapshot.run.target_plate;
 return <main className="atlas-front">
  <section className="atlas-hero" ref={hero} data-map-scene id="network" aria-label="Delhi camera network" tabIndex={-1}>
   <div className="atlas-hero-sticky">
    <div className="atlas-hero-map"><MapView cameras={snapshot.cameras} selectedCamera={selectedCamera} onCamera={setSelectedCamera} observations={observations} pageScroll cinematic/></div>
    <div className="atlas-hero-shade" ref={heroShade}/>
    <div className="atlas-hero-copy" ref={heroCopy}>
     <h1><span>A city</span><strong>in motion.</strong></h1>
     <div className="atlas-hero-intro"><p>Vehicle intelligence.<br/>Across Delhi. Within reach.</p><a href="#journey" className="atlas-action" onClick={e=>goToSection(e,'journey')}>Explore a journey <ArrowUpRight size={19}/></a></div>
    </div>
    <div className="atlas-network-note" ref={networkNote}><span>Delhi, in view.</span><p>Select a camera to open its recorded sightings.</p></div>
    {selected&&<div className="atlas-camera-selection"><div><span className="mono">{selected.id} / {selected.status}</span><strong>{selected.name}</strong></div><Link to={'/activity?camera='+selected.id}>View sightings <ArrowUpRight size={17}/></Link><button className="icon-btn" aria-label="Clear camera selection" onClick={()=>setSelectedCamera(undefined)}><X size={17}/></button></div>}
    <div className="atlas-hero-footer"><span><i className="dot online"/> {snapshot.cameras.length} camera locations <span className="atlas-footer-separator">/</span> Delhi</span><span className="atlas-demo-label">SIMULATED NETWORK</span><a href="#journey" onClick={e=>goToSection(e,'journey')}>Scroll to follow <ArrowDown size={15}/></a></div>
   </div>
  </section>

  <section className="atlas-journey" ref={journey} id="journey" aria-labelledby="journey-title" tabIndex={-1}>
   <div className="atlas-journey-sticky">
    <div className="atlas-journey-heading"><h2 id="journey-title"><span>Separate sightings.</span><strong>One recorded journey.</strong></h2><p>Follow the observations.<br/>Keep the gaps in view.</p></div>
    {vehicle.isError?<ErrorState error={vehicle.error} retry={()=>vehicle.refetch()}/>:vehicle.isLoading||seed.isLoading?<Loading/>:!observations.length?<Empty title="No recorded journey yet">Search a vehicle or process a sample to begin.</Empty>:<div className="atlas-journey-body">
     <div className="atlas-journey-evidence">
      <div className="atlas-journey-identity"><Plate value={selectedPlate}/><span>{target.data?.vehicle_id?'Recognition + simulated replay':'Seeded demonstration journey'}</span></div>
      <div className="atlas-stop-heading"><span className="mono">{String(activeStop+1).padStart(2,'0')} / {String(observations.length).padStart(2,'0')}</span><span className="mono">{stop?time(stop.observed_at,true):'—'} IST</span></div>
      <div className="atlas-stop-copy" key={stop?.id}><h3>{stop?.camera.name}</h3><p>{stop?.camera.direction} · {stop?.camera_id}</p><p>{stop?.source_kind==='real_inference'?'Real sample recognition. Plate and evidence are available for inspection.':'Recorded at a simulated camera location. This is an observation, not a continuously known position.'}</p></div>
      <div className="atlas-stop-selector" aria-label="Recorded camera observations">{observations.map((o,i)=><button key={o.id} aria-label={'Show sighting '+(i+1)+' at '+o.camera.name} aria-pressed={i===activeStop} onClick={()=>step(i)}><span>{String(i+1).padStart(2,'0')}</span><i className={i<=activeStop?'passed':''}/></button>)}</div>
      <div className="atlas-step-controls"><button className="icon-btn" aria-label="Previous sighting" disabled={activeStop===0} onClick={()=>step(activeStop-1)}><ArrowLeft size={19}/></button><button className="icon-btn" aria-label="Next sighting" disabled={activeStop>=observations.length-1} onClick={()=>step(activeStop+1)}><ArrowRight size={19}/></button><button className="text-button" onClick={()=>stop&&onEvidence(stop)}>View evidence <ArrowUpRight size={16}/></button></div>
      <Link to={vehicleUrl} className="atlas-text-link">Open full vehicle history <ArrowUpRight size={17}/></Link>
     </div>
     <div className="atlas-journey-map"><MapView cameras={snapshot.cameras.filter(c=>observations.some(o=>o.camera_id===c.id))} observations={observations} focusObservationId={stop?.id} selectedCamera={stop?.camera_id} onCamera={id=>{const index=observations.findIndex(o=>o.camera_id===id);if(index>=0)step(index)}} pageScroll/>
      <div className="atlas-route-caption"><span><i/> Estimated connections between sightings</span><span>{date(stop?.observed_at)} · IST</span></div>
     </div>
    </div>}
    <div className="atlas-journey-foot"><span>Solid connection. Incomplete coverage.</span><p>Camera locations are simulated. Lines connect accepted observations; they do not verify the roads travelled.</p><a href="#operations-overview" onClick={e=>goToSection(e,'operations-overview')} aria-label="Go to operations overview"><ArrowDown size={21}/></a></div>
   </div>
  </section>

  <section className="atlas-operations" id="operations-overview" aria-labelledby="operations-title" tabIndex={-1}>
   <div className="atlas-section-heading"><h2 id="operations-title">The network,<br/><strong>at a glance.</strong></h2><span className="command-today">{today}<small>LOCAL WORKSPACE · IST</small></span></div>
   <div className="atlas-data-panel">
    <div className="atlas-data-summary">
     <div className="atlas-data-tabs" role="tablist" aria-label="Network overview">{(['coverage','passages','alerts'] as const).map(t=><button role="tab" id={'overview-tab-'+t} aria-selected={subject===t} tabIndex={subject===t?0:-1} aria-controls="network-overview-panel" key={t} onClick={()=>setSubject(t)} onKeyDown={e=>{const tabs=['coverage','passages','alerts'] as const;const index=tabs.indexOf(t);const next=e.key==='ArrowRight'?(index+1)%3:e.key==='ArrowLeft'?(index+2)%3:e.key==='Home'?0:e.key==='End'?2:-1;if(next>=0){e.preventDefault();setSubject(tabs[next]);document.getElementById('overview-tab-'+tabs[next])?.focus()}}}>{t==='coverage'?'Coverage':t==='passages'?'Sightings':'Alerts'}</button>)}</div>
     <div className="atlas-data-reading" id="network-overview-panel" role="tabpanel" aria-labelledby={'overview-tab-'+subject} tabIndex={0}>
      <div className="atlas-data-value">{subject==='coverage'?online:subject==='passages'?number(snapshot.summary.passages):snapshot.summary.active_alerts}{subject==='coverage'&&<span> / {snapshot.cameras.length}</span>}</div>
      <h3>{subject==='coverage'?'Cameras online':subject==='passages'?'Recorded passages':'Active alerts'}</h3>
      <p>{subject==='coverage'?'Coverage is limited to monitored locations. Offline cameras leave gaps.':subject==='passages'?number(snapshot.summary.identified)+' accepted plate identities in the current scenario.':'Priority first. Repeated sightings update an existing alert episode.'}</p>
      <Link className="atlas-text-link" to={subject==='coverage'?'/cameras':subject==='passages'?'/activity':'/alerts'}>{subject==='coverage'?'Inspect camera health':subject==='passages'?'Explore sightings':'Manage alerts'} <ArrowUpRight size={17}/></Link>
     </div>
    </div>
    <div className="atlas-data-visual">
     {subject==='coverage'?<><div className="atlas-diagram-caption"><span>Central & East Delhi</span><span>SIMULATED LOCATIONS</span></div><CameraDiagram cameras={snapshot.cameras}/><div className="atlas-diagram-legend"><span><i className="dot online"/>Online</span><span><i className="dot amber"/>Degraded</span><span><i className="dot offline"/>Offline</span></div></>:subject==='passages'?traffic.isError?<ErrorState error={traffic.error} retry={()=>traffic.refetch()}/>:!traffic.data?<Loading/>:<><div className="atlas-diagram-caption"><span>Observed flow</span><span>PASSAGES / CAMERA</span></div><div className="atlas-flow-chart">{traffic.data.camera_flow.map((c:Camera)=><Link key={c.id} to={'/activity?camera='+c.id} aria-label={c.name+': '+c.passages+' passages'}><span className="atlas-flow-count">{c.passages}</span><div className="atlas-flow-track"><i style={{height:Math.max(1,(c.passages||0)/Math.max(...traffic.data.camera_flow.map((x:Camera)=>x.passages||1))*100)+'%'}}/></div><span className="mono">{c.id}</span></Link>)}</div><p className="atlas-chart-note">Event counts in the selected scenario. Counts are not road density.</p></>:topAlert?<div className="atlas-featured-alert"><span className={'atlas-alert-priority '+topAlert.priority}><ShieldAlert size={17}/>{topAlert.priority} priority</span><Plate value={topAlert.observation.plate}/><h3>{topAlert.reason}</h3><p>{topAlert.observation.camera.name} · {time(topAlert.observation.observed_at)} IST</p><button className="atlas-action" onClick={()=>onAlert(topAlert)}>Review observation <ArrowUpRight size={18}/></button></div>:<Empty title="No active alerts">New watchlist matches will appear here.</Empty>}
    </div>
   </div>
   <div className="atlas-demo-controls">{toolbar}<div className="atlas-demo-explainer"><ScanLine size={18}/><p>Recognize a real Indian plate. Replay its simulated journey across four cameras.</p><button className="text-button" onClick={onRecognize}>Process target sample <ArrowUpRight size={16}/></button></div></div>
  </section>

  <section className="atlas-workspaces" aria-labelledby="workspaces-title">
   <div className="atlas-section-heading"><h2 id="workspaces-title">Look closer.</h2><p>The details belong<br/>in your workspace.</p></div>
   <Link to="/investigations" className="atlas-workspace-link"><span>Find a vehicle</span><p>Registration search · latest and past journeys</p><ArrowUpRight/></Link>
   <Link to="/appearance" className="atlas-workspace-link"><span>Follow a description</span><p>Color, appearance, details · assisted by Jev</p><ArrowUpRight/></Link>
   <Link to="/activity" className="atlas-workspace-link"><span>Review the activity</span><p>Recent sightings · priority alerts · evidence</p><ArrowUpRight/></Link>
   <div className="atlas-closing"><Link to="/" aria-label="SylRak home">SylRak<span>VEHICLE INTELLIGENCE</span></Link><p>Observed locations.<br/>Informed investigations.</p><a href="#network" className="atlas-text-link" onClick={e=>goToSection(e,'network')}>Back to the city <ArrowUpRight size={17}/></a></div>
  </section>
 </main>;
}
