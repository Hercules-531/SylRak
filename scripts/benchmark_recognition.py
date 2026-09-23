"""Deterministic predictions, then scoring. Reference text never selects a prediction."""
import hashlib,json,re,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.inference import load_models,deduplicate_detections,box_iou
from backend.recognition_options import prepare_crop,single_line,PaddleCropReader
OUT=ROOT/'artifacts/recognition-upgrade';OUT.mkdir(parents=True,exist_ok=True)

def norm(t):return re.sub('[^A-Z0-9]','',(t or '').upper())
def distance(a,b):
    row=list(range(len(b)+1))
    for i,c in enumerate(a,1):
        nxt=[i]
        for j,d in enumerate(b,1):nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(c!=d)))
        row=nxt
    return row[-1]
def principal(detections):
    def score(d):
        b=d.get('plate_box')
        return ((b[2]-b[0])*(b[3]-b[1])*(d.get('plate_confidence') or 0)) if b else -1
    return max(deduplicate_detections(detections),key=score,default={})
def summary(rows,name):
    usable=[r for r in rows if name in r['predictions']]
    return {'n':len(usable),'exact':sum(norm(r['predictions'][name]['text'])==r['truth'] for r in usable),
      'accuracy':sum(norm(r['predictions'][name]['text'])==r['truth'] for r in usable)/max(1,len(usable)),
      'cer':sum(distance(r['truth'],norm(r['predictions'][name]['text'])) for r in usable)/max(1,sum(len(r['truth']) for r in usable)),
      'unreadable':sum(not norm(r['predictions'][name]['text']) for r in usable),
      'mean_crop_seconds':sum(r['predictions'][name].get('seconds',0) for r in usable)/max(1,len(usable))}

def main():
    manifest=json.loads((ROOT/'assets/samples/manifest.json').read_text())['samples']
    batch=json.loads((ROOT/'artifacts/recognition/batch.json').read_text())
    boxes=json.loads((OUT/'plate-boxes.json').read_text())
    _,alpr,_=load_models()
    try:paddle=PaddleCropReader(ROOT/'assets/models/paddle/en_PP-OCRv5_mobile_rec');paddle_error=None
    except Exception as e:paddle=None;paddle_error=type(e).__name__+': '+str(e)[:400]
    records=[];seen=set();demo_groups={s.get('vehicle_group') for s in manifest if s.get('split')=='demo'}
    for s in manifest:
        if s.get('split')!='evaluation' or s['sha256'] in seen or s.get('vehicle_group') in demo_groups:continue
        seen.add(s['sha256']);frame=np.asarray(ImageOps.exif_transpose(Image.open(ROOT/'assets/samples'/s['filename'])).convert('RGB'))[:,:,::-1].copy()
        selected=principal(batch.get(s['id'],{}).get('detections',[]));b=selected.get('plate_box')
        predictions={'baseline':{'text':selected.get('raw_plate') or '', 'confidence':selected.get('ocr_confidence')}}
        if b:
            crop=prepare_crop(frame,b);prepared=single_line(crop)
            start=time.perf_counter();reading=alpr.ocr.predict(prepared)
            predictions['cct_preprocessed']={'text':reading.text if reading else '', 'seconds':time.perf_counter()-start}
            if paddle:
                start=time.perf_counter()
                try:text,confidence=paddle.read(prepared);predictions['paddle']={'text':text,'confidence':confidence,'seconds':time.perf_counter()-start}
                except Exception as e:paddle_error=type(e).__name__+': '+str(e)[:400];paddle=None
        else:
            predictions['cct_preprocessed']={'text':''}
            if paddle:predictions['paddle']={'text':''}
        # Only now load the answer for scoring; never used for selection or preprocessing.
        truth=norm(s['ground_truth']);ann=boxes.get(s['id'])
        overlap=max((box_iou(b,g) for g in ann),default=0) if b and ann else None
        records.append({'sample':s['id'],'truth':truth,'group':s.get('vehicle_group'),
          'subset':'validation' if int(hashlib.sha256(s.get('vehicle_group',s['id']).encode()).hexdigest(),16)%4==0 else 'exploratory_holdout',
          'predictions':predictions,'selected_box':b,'annotation_iou':overlap})
        print(s['id'],{k:v['text'] for k,v in predictions.items()},flush=True)
        (OUT/'comparison-rows.json').write_text(json.dumps(records,indent=2))
    variants=['baseline','cct_preprocessed']+(['paddle'] if any('paddle' in r['predictions'] for r in records) else [])
    report={'method':'Largest area times plate-detector score after application deduplication; no answer-key selection. Same selected crop for both alternative OCR pipelines.',
      'limitations':['Small previously inspected convenience sample; not an untouched final test set.','Only a subset has publisher plate boxes. No vehicle box annotations; vehicle precision/recall unavailable.','Not enough independent real test images to establish 90% accuracy.'],
      'all':{v:summary(records,v) for v in variants},
      'validation':{v:summary([r for r in records if r['subset']=='validation'],v) for v in variants},
      'exploratory_holdout':{v:summary([r for r in records if r['subset']=='exploratory_holdout'],v) for v in variants},
      'paddle_error':paddle_error,'spatially_annotated_images':sum(boxes.get(r['sample']) is not None for r in records),
      'prediction_rows':'comparison-rows.json'}
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
