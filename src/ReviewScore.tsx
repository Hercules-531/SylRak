export type ReviewAssessment={score:number|null;scale:number;band:string;warning:string;reasons:{code:string;label:string;points:number}[];scope:string;accepted_history_count:number;experimental:boolean};

export function ReviewWarning(){return <p className="review-warning">Experimental suspicion scores may be inaccurate. These are rule-based points, not the probability that a vehicle is stolen. A low score does not clear a vehicle.</p>}

export default function ReviewScore({value,compact=false}:{value?:ReviewAssessment|null;compact?:boolean}){
 if(!value)return <span className="muted">Not assessed</span>;
 return <details className={'review-assessment'+(compact?' compact':'')}>
  <summary><span className="review-score-value">{value.score==null?'Unknown':`${value.score}/100`}</span><span>{compact?'Suspicion score':'Experimental suspicion score'}</span></summary>
  {!compact&&<p className="review-score-caption">Experimental · {value.band} · Show contributing signals</p>}
  <div className="review-explanation"><p>{value.warning}</p>
  {value.reasons.length?<ul>{value.reasons.map(r=><li key={r.code}><span>{r.label}</span><strong>+{r.points}</strong></li>)}</ul>:<p>{value.score==null?'Insufficient evidence for a score.':'No configured review signals found. This does not establish lawful ownership.'}</p>}
  <p>{value.scope} Accepted sightings: {value.accepted_history_count}.</p>
  <p>Watchlists and camera locations are demonstration data. This score does not create alerts or change vehicle associations.</p></div>
 </details>
}
