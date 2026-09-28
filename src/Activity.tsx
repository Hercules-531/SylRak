import {Link, useSearchParams} from 'react-router-dom';
import {ArrowUp, ArrowUpRight} from 'lucide-react';
import {time,useGet,type Snapshot,type Alert,type Observation} from './api';
import {Badge,Empty,ErrorState,Loading,ObservationTable,Plate,SourceBadge} from './ui';

export default function ActivityPage({snapshot,onEvidence,onAlert}:{snapshot:Snapshot;onEvidence:(o:Observation)=>void;onAlert:(a:Alert)=>void}){
 const [params]=useSearchParams();const selectedCamera=params.get('camera');
 const c=snapshot.cameras.find(c=>c.id===selectedCamera);
 const detail=useGet<any>('/cameras/'+selectedCamera,!!selectedCamera);
 const priorities:Record<string,number>={critical:0,high:1,medium:2};
 const alerts=[...snapshot.alerts].sort((a,b)=>(priorities[a.priority]??3)-(priorities[b.priority]??3)||b.updated_at-a.updated_at);
 return (
    <section className="activity-records page-content" aria-label="Camera activity">
      <section className="panel recent-panel" id="recent-sightings" tabIndex={-1} aria-labelledby="recent-title">
        <div className="panel-heading"><h2 id="recent-title">{c?'Sightings at '+c.name:'Recent sightings'}<span className="panel-counter">{c?detail.data?.observations.length||0:snapshot.recent.length}</span></h2>
          <Link className="text-button" to={'/investigations'+(c?'?camera='+c.id:'')}>Search history <ArrowUpRight size={15}/></Link>
        </div>
        {c&&detail.isLoading?<Loading/>:c&&detail.isError?<ErrorState error={detail.error} retry={()=>detail.refetch()}/>:<ObservationTable items={c?detail.data?.observations||[]:snapshot.recent} onEvidence={onEvidence} compact/>}
      </section>

      <section className="panel command-alerts" id="priority-alerts" tabIndex={-1} aria-labelledby="priority-title">
        <div className="panel-heading"><h2 id="priority-title">Priority alerts<span className="panel-counter red-counter">{snapshot.summary.active_alerts}</span></h2><Link to="/alerts" className="text-button" aria-label="View all alerts">Manage alerts <ArrowUpRight size={15}/></Link></div>
        {alerts.length?<div className="table-scroll"><table className="data-table" aria-label="Priority alerts"><thead><tr><th>Priority</th><th>Observed plate</th><th>Reason / matching method</th><th>Last observed camera</th><th>Updated · IST</th><th>Status</th><th><span className="sr-only">Investigation</span></th></tr></thead>
          <tbody>{alerts.map(a=><tr key={a.id}>
            <td><Badge tone={a.priority==='medium'?'amber':'red'}>{a.priority}</Badge></td>
            <td><button className="text-button plate-link" onClick={()=>onAlert(a)} aria-label={'Investigate alert for '+(a.observation.plate||'unreadable plate')}><Plate value={a.observation.plate} small/><ArrowUpRight size={13}/></button>{a.watchlist?.plate&&a.watchlist.plate!==a.observation.plate&&<small className="command-expected">Expected: {a.watchlist.plate}</small>}</td>
            <td><span className="command-alert-reason">{a.match_method==='possible'?'Possible watchlist match':a.category==='route pattern'?'Repeated route pattern':a.category+' vehicle'}</span><small className="command-table-meta">{a.match_method==='exact'?'Exact match':'Review required'} · {a.sighting_count} sighting{a.sighting_count===1?'':'s'}</small></td>
            <td><span className="mono camera-code">{a.observation.camera_id}</span><span className="table-location">{a.observation.camera.name}</span></td>
            <td><span className="mono">{time(a.updated_at,true)}</span><small className="command-table-meta"><SourceBadge source={a.observation.source_kind}/></small></td>
            <td><span className="command-alert-state">{a.status}</span></td>
            <td><button className="icon-btn" aria-label={'Open alert '+a.id} onClick={()=>onAlert(a)}><ArrowUpRight size={17}/></button></td>
          </tr>)}</tbody></table></div>:<Empty title="No active alerts">New watchlist matches appear here.</Empty>}
      </section>
      <Link className="command-return" to="/">Back to city overview <ArrowUp size={16}/></Link>
    </section>
 );
}
