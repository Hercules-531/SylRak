"""Download the explicitly selected public inputs. No model weights from datasets."""
from pathlib import Path
import sys, json, re, urllib.request, urllib.parse, zipfile, subprocess, concurrent.futures, hashlib
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'
# Camera limits stay at 77.17-77.34 E, 28.56-28.69 N (MapView maxBounds). The extract adds a
# ~10 km margin so tilted and narrow views never reach the edge of the tile data.
MAP_BBOX=(77.07,28.50,77.44,28.76)
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'SylRak-SIH-prototype/0.1'})
    with urllib.request.urlopen(req,timeout=120) as r:return r.read()
def samples():
    folder=ASSETS/'samples';folder.mkdir(parents=True,exist_ok=True)
    base='https://www.kaggle.com/api/v1/datasets/list/tkm22092/indian-number-plate-images'
    files=[];token=None
    for _ in range(40):
        data=json.loads(fetch(base+('?pageToken='+urllib.parse.quote(token) if token else '')))
        batch=data.get('datasetFiles',[]);files+=batch;token=data.get('nextPageToken')
        if not token:break
    files={f['name']:f for f in files if f['name'].lower().endswith(('.jpg','.jpeg','.png')) and '/images/' in f['name']}
    names=sorted(files)
    # Evenly spaced source samples avoid selecting only one consecutive burst.
    names=[names[round(i*(len(names)-1)/min(59,len(names)-1))] for i in range(min(60,len(names)))]
    def download(pair):
        i,name=pair;target=folder/f'sample-{i+1:03d}.jpg'
        if not target.exists():
            url='https://www.kaggle.com/api/v1/datasets/download/tkm22092/indian-number-plate-images/'+urllib.parse.quote(name,safe='')
            raw=fetch(url)
            if raw[:2]==b'PK':
                import io
                with zipfile.ZipFile(io.BytesIO(raw)) as z:raw=z.read(next(n for n in z.namelist() if n.lower().endswith(('.jpg','.png'))))
            target.write_bytes(raw)
        from PIL import Image
        with Image.open(target) as image:width,height=image.size
        return {'id':target.stem,'filename':target.name,'original_filename':name,'ground_truth':None,'split':'unreviewed','vehicle_group':None,'width':width,'height':height,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'license':'CC0-1.0 (publisher declaration)','source_url':'https://www.kaggle.com/datasets/tkm22092/indian-number-plate-images'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        result=list(pool.map(download,enumerate(names)))
    (folder/'manifest.json').write_text(json.dumps({'dataset':'tkm22092/indian-number-plate-images','dataset_file_creation_date':files[names[0]].get('creationDate'),'declared_license':'CC0-1.0','target_sample_id':None,'samples':result},indent=2),encoding='utf-8')
    print(f'Downloaded {len(result)} photographs for manual review',flush=True)
def maps():
    folder=ASSETS/'map';folder.mkdir(parents=True,exist_ok=True)
    tools=ROOT/'runtime'/'tools';tools.mkdir(parents=True,exist_ok=True)
    exe=tools/'pmtiles.exe'
    if not exe.exists():
        archive=tools/'pmtiles.zip';archive.write_bytes(fetch('https://github.com/protomaps/go-pmtiles/releases/download/v1.31.2/go-pmtiles_1.31.2_Windows_x86_64.zip'))
        with zipfile.ZipFile(archive) as z:exe.write_bytes(z.read(next(n for n in z.namelist() if n.endswith('pmtiles.exe'))))
    builds=json.loads(fetch('https://build-metadata.protomaps.dev/builds.json'))
    build=sorted([b for b in builds if b['key'].endswith('.pmtiles')],key=lambda b:b['key'],reverse=True)[0]
    source='https://build.protomaps.com/'+build['key']
    target=folder/'delhi.pmtiles';provenance=folder/'provenance.json'
    current=json.loads(provenance.read_text(encoding='utf-8')).get('bbox') if provenance.exists() else None
    if not target.exists() or current!=list(MAP_BBOX):
        partial=folder/'delhi.pmtiles.partial';partial.unlink(missing_ok=True)
        subprocess.run([str(exe),'extract',source,str(partial),'--bbox='+','.join(map(str,MAP_BBOX)),'--maxzoom=15','--download-threads=6'],check=True)
        partial.replace(target)
    provenance.write_text(json.dumps({'source':source,'build':build,'bbox':list(MAP_BBOX),'attribution':'© OpenStreetMap contributors · Protomaps','license':'ODbL-1.0 produced work','cli_version':'1.31.2','sha256':hashlib.sha256(target.read_bytes()).hexdigest()},indent=2))
    print('Delhi PMTiles ready',target.stat().st_size,flush=True)
if __name__=='__main__':
    {'samples':samples,'map':maps}[sys.argv[1]]()
