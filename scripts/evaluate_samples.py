import json,re,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.benchmark_recognition import principal
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
    selected=principal(batch.get(sample['id'],{}).get('detections',[]))
    best=norm(selected.get('raw_plate'))
    rows.append({'sample_id':sample['id'],'ground_truth':truth,'best_reading':best or None,'edit_distance':distance(truth,best),'exact':truth==best})
result={'evaluated_images':len(rows),'exact_images':sum(x['exact'] for x in rows),'exact_accuracy':sum(x['exact'] for x in rows)/len(rows),'character_error_rate':sum(x['edit_distance'] for x in rows)/sum(len(x['ground_truth']) for x in rows),'method':'Deterministic principal plate by area times detector confidence after application deduplication. Reference text never selects a prediction. Exploratory sample, not an untouched final test set.','rows':rows}
out=ROOT/'artifacts/evaluation-corrected.json';out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
