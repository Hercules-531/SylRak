"""Fetch publisher annotations and OCR weights; never download dataset model weights."""
import concurrent.futures,hashlib,io,json,sys,time,urllib.request,urllib.parse,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts'/'recognition-upgrade';OUT.mkdir(parents=True,exist_ok=True)

def fetch(url):
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'SylRak-research/0.2'})
            with urllib.request.urlopen(req,timeout=60) as r:return r.read()
        except Exception:
            if attempt==2:raise
            time.sleep(1)

def get_file(url,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        raw=fetch(url)
        if raw[:2]==b'PK' and path.suffix not in ['.keras','.zip']:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:raw=z.read(z.namelist()[0])
        path.write_bytes(raw)
    return path

def main():
    index=OUT/'publisher-files.json'
    if index.exists():files=json.loads(index.read_text())
    else:
        files=[];token=''
        for page in range(40):
            u='https://www.kaggle.com/api/v1/datasets/list/tkm22092/indian-number-plate-images?pageSize=1000'
            if token:u+='&pageToken='+urllib.parse.quote(token)
            d=json.loads(fetch(u));files.extend(d['datasetFiles']);token=d.get('nextPageToken')
            if not token:break
        index.write_text(json.dumps(files,indent=2))
    annotations={Path(f['name']).stem:f['name'] for f in files if f['name'].endswith('.txt')}
    manifest=json.loads((ROOT/'assets/samples/manifest.json').read_text())
    def label(sample):
        name=annotations.get(Path(sample['original_filename']).stem)
        if not name:return sample['id'],None
        url='https://www.kaggle.com/api/v1/datasets/download/tkm22092/indian-number-plate-images/'+urllib.parse.quote(name,safe='')
        p=get_file(url,OUT/'annotations'/f"{sample['id']}.txt")
        boxes=[]
        for line in p.read_text().splitlines():
            parts=line.split()
            if len(parts)!=5:continue
            _,x,y,w,h=map(float,parts);iw,ih=sample['width'],sample['height']
            boxes.append([(x-w/2)*iw,(y-h/2)*ih,(x+w/2)*iw,(y+h/2)*ih])
        return sample['id'],boxes
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        boxes=dict(pool.map(label,manifest['samples']))
    (OUT/'plate-boxes.json').write_text(json.dumps(boxes,indent=2))
    print('Annotated images',sum(bool(v) for v in boxes.values()),flush=True)
    base='https://github.com/ankandrew/cnn-ocr-lp/releases/download/arg-plates/'
    for name in ['cct_s_v2_global.keras','cct_s_v2_global_model_config.yaml','cct_s_v2_global_plate_config.yaml']:
        get_file(base+name,ROOT/'assets/models/training'/name)
    paddle=ROOT/'assets/models/paddle/en_PP-OCRv5_mobile_rec'
    for name in ['inference.json','inference.pdiparams','inference.yml']:
        get_file('https://huggingface.co/PaddlePaddle/en_PP-OCRv5_mobile_rec/resolve/main/'+name,paddle/name)
    (OUT/'provenance.json').write_text(json.dumps({'annotations':'https://www.kaggle.com/datasets/tkm22092/indian-number-plate-images','annotation_license':'CC0-1.0, publisher declaration, version 2','cct_weights':base,'paddle_weights':'https://huggingface.co/PaddlePaddle/en_PP-OCRv5_mobile_rec','models':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for root in [ROOT/'assets/models/training',paddle] for p in root.glob('*') if p.is_file()]},indent=2))
    print('Recognition inputs ready',flush=True)

if __name__=='__main__':main()
