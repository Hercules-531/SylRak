import {useQuery} from '@tanstack/react-query';
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
  const response=await fetch('/api/v1'+path,{credentials:'same-origin',...options,headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...options.headers}});
  if(!response.ok){const body=await response.json().catch(()=>({detail:response.statusText}));throw new Error(typeof body.detail==='string'?body.detail:body.detail?.[0]?.msg||'Request failed');}
  return response.json();
}
export function useGet<T=any>(path:string,enabled=true){return useQuery<T>({queryKey:[path],queryFn:()=>api<T>(path),enabled});}
export const post=(path:string,body:unknown)=>api(path,{method:'POST',body:JSON.stringify(body)});
export const patch=(path:string,body:unknown)=>api(path,{method:'PATCH',body:JSON.stringify(body)});
export const time=(seconds:number|null|undefined,full=false)=>seconds==null?'—':new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',hour:'2-digit',minute:'2-digit',second:full?'2-digit':undefined,hour12:false}).format(new Date(seconds*1000));
export const date=(seconds:number|null|undefined)=>seconds==null?'—':new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',day:'2-digit',month:'short',year:'numeric'}).format(new Date(seconds*1000));
export const pct=(value:number|null|undefined)=>value==null?'—':(value*100).toFixed(1)+'%';
export const number=(v:number|undefined)=>new Intl.NumberFormat('en-IN').format(v||0);
export type Camera={id:string;name:string;road:string;lat:number;lon:number;direction:string;status:string;heartbeat:number;passages?:number};
export type Observation={id:string;plate:string|null;raw_plate:string|null;canonical_plate:string|null;vehicle_id:string|null;camera_id:string;camera:Camera;observed_at:number;ingested_at:number;run_id:string;source_kind:string;vehicle_type:string;color:string;ocr_confidence:number|null;vehicle_confidence:number|null;plate_confidence:number|null;status:string;evidence:any;association:any;details:any;format:string};
export type Alert={id:string;vehicle_id:string|null;priority:string;category:string;reason:string;match_method:string;status:string;created_at:number;updated_at:number;observation:Observation;watchlist:any;subject:string;notification:any;sighting_count:number};
export type Snapshot={run:any;cameras:Camera[];recent:Observation[];alerts:Alert[];summary:any;models:any};
