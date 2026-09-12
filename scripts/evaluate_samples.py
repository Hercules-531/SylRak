import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'assets/samples/manifest.json').read_text())
batch=json.loads((ROOT/'artifacts/recognition/batch.json').read_text())
def norm(value):return re.sub(r'[^A-Z0-9]','',(value or '').upper())
def distance(a,b):
    previous=list(range(len(b)+1))
    for i,left in enumerate(a,1):
        current=[i]
        for j,right in enumerate(b,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(left!=right)))
        previous=current
    return previous[-1]

rows=[]
for sample in manifest['samples']:
    if sample.get('split')!='evaluation':continue
    truth=norm(sample['ground_truth'])
    candidates=[norm(x.get('raw_plate')) for x in batch.get(sample['id'],{}).get('detections',[]) if norm(x.get('raw_plate'))]
    best=min(candidates,key=lambda value:distance(truth,value)) if candidates else ''
    rows.append({'sample_id':sample['id'],'ground_truth':truth,'best_reading':best or None,'edit_distance':distance(truth,best),'exact':truth==best})
result={'evaluated_images':len(rows),'exact_images':sum(x['exact'] for x in rows),'exact_accuracy':sum(x['exact'] for x in rows)/len(rows),'character_error_rate':sum(x['edit_distance'] for x in rows)/sum(len(x['ground_truth']) for x in rows),'method':'Best OCR candidate per manually transcribed principal plate; post-inference comparison only.','rows':rows}
out=ROOT/'artifacts/evaluation.json';out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
