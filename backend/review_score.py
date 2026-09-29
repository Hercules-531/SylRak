"""Explainable demo review points. Never a probability, identity decision, or alert trigger."""
from sqlalchemy import select
from .db import Observation, Watchlist

WARNING = ('Experimental: may be inaccurate. This rule-based score is not a probability '
           'that a vehicle is stolen, proof of an offence, or grounds for enforcement.')

def theft_review(s, observation):
    o=observation
    accepted=o.status=='accepted' and bool(o.vehicle_id)
    history=[o]
    if accepted:
        history=list(s.scalars(select(Observation).where(
            Observation.vehicle_id==o.vehicle_id,Observation.status=='accepted',
            Observation.run_id==o.run_id,Observation.observed_at<=o.observed_at,
            Observation.observed_at>=o.observed_at-1200).order_by(Observation.observed_at,Observation.id)))
    reasons=[]
    def add(code,label,points):reasons.append({'code':code,'label':label,'points':points})
    watches=list(s.scalars(select(Watchlist).where(Watchlist.active==True,
          (Watchlist.valid_from==None)|(Watchlist.valid_from<=o.observed_at),
          (Watchlist.valid_until==None)|(Watchlist.valid_until>=o.observed_at))))
    exact=[w for w in watches if w.plate==o.plate and o.plate]
    if exact and accepted and (o.ocr_confidence or 0)>=.9:
        serious=any(w.category in ['stolen','wanted'] for w in exact)
        add('watchlist_exact','Accepted exact match to an active demonstration '+('stolen/wanted' if serious else 'flagged')+' record',70 if serious else 45)
    elif o.plate and any(w.plate==o.plate or (len(w.plate)==len(o.plate) and sum(a!=b for a,b in zip(w.plate,o.plate))==1) for w in watches):
        add('watchlist_uncertain','Uncertain watchlist resemblance; identity needs verification',15)
    a=o.details.get('appearance',{})
    if a.get('plate_visibility')=='visibly absent':
        add('plate_absent','Plate recorded as visibly absent; may have a lawful explanation',12)
    if a.get('visibility')=='heavily obscured':
        add('covered','Vehicle heavily obscured; hidden attributes stay unknown',8)
    if o.status=='conflict':
        add('identity_conflict','Conflicting association; check OCR, clocks and possible cloned plates',15)
    # Collapse duplicate passages. Repeated copies never increase points.
    visits=[];seen=set()
    for sighting in history:
        passage=(sighting.camera_id,sighting.track_id)
        if passage in seen:continue
        seen.add(passage)
        if not visits or visits[-1].camera_id!=sighting.camera_id:visits.append(sighting)
    for i in range(len(visits)-3):
        p,q,r,t=visits[i:i+4]
        if p.camera_id==r.camera_id and q.camera_id==t.camera_id and p.camera_id!=q.camera_id and t.observed_at-p.observed_at<=1200:
            add('repeated_movement',f'{p.camera_id} → {q.camera_id} → {r.camera_id} → {t.camera_id} within 20 minutes; ordinary repeat journeys can look similar',20)
            break
    enough=bool(reasons) or accepted or a.get('visibility')=='clear'
    score=min(95,sum(r['points'] for r in reasons)) if enough else None
    return {'score':score,'scale':100,'experimental':True,'calibrated':False,
            'label':'Suspicion score','warning':WARNING,'reasons':reasons,
            'band':'Insufficient evidence' if score is None else 'Elevated review' if score>=60 else 'Review signals' if score>0 else 'No listed signals',
            'accepted_history_count':len(history) if accepted else 0,'as_of':o.observed_at,
            'scope':'This candidate and accepted observations in this run, over the preceding 20 scenario minutes.',
            'limitations':['Demonstration watchlists and camera locations are simulated.',
                          'A low score does not establish that a vehicle is safe or lawfully owned.',
                          'Appearance-only candidates are not connected across cameras.'],
            'version':'review-rules-1'}
