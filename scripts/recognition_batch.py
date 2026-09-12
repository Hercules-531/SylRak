import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.inference import infer_image
from backend.config import ASSETS,ROOT
folder=ROOT/'artifacts'/'recognition';folder.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ASSETS/'samples'/'manifest.json').read_text())
out=folder/'batch.json';records=json.loads(out.read_text()) if out.exists() else {}
for sample in manifest['samples']:
    if sample['id'] in records:continue
    try:
        result=infer_image(ASSETS/'samples'/sample['filename'],folder/'crops')
        records[sample['id']]=result
        print(sample['id'],[(x['raw_plate'],round(x['ocr_confidence'] or 0,3)) for x in result['detections']],flush=True)
    except Exception as e:records[sample['id']]={'error':str(e)};print(sample['id'],str(e),flush=True)
    out.write_text(json.dumps(records,indent=2))
