"""Real inference only. Ground-truth annotations are never inputs to these models."""
from pathlib import Path
import time, json, hashlib, uuid, os, importlib.metadata
import numpy as np
from PIL import Image, ImageOps
from .config import ASSETS, EVIDENCE

_models=None

def box_iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return intersection/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)

def deduplicate_detections(found):
    # One visible registration per detected vehicle; suppress overlap from nested vehicle regions.
    groups={}
    for item in found:
        groups.setdefault(tuple(item['vehicle_box'] or []),[]).append(item)
    candidates=[]
    for readings in groups.values():
        def area_score(d):
            b=d.get('plate_box')
            return (b[2]-b[0])*(b[3]-b[1])*(d.get('plate_confidence') or 0) if b else 0
        candidates.append(max(readings,key=area_score))
    retained=[]
    for item in sorted(candidates,key=lambda d:d.get('plate_confidence') or 0,reverse=True):
        box=item.get('plate_box')
        if box and any(other.get('plate_box') and box_iou(box,other['plate_box'])>=.35 for other in retained):continue
        retained.append(item)
    return retained
def load_models():
    global _models
    if _models is not None: return _models
    import onnxruntime as ort
    from fast_alpr import ALPR
    import fast_plate_ocr.inference.hub as ocr_hub
    import open_image_models.detection.core.hub as detector_hub
    from ultralytics import YOLO
    import torch
    torch.set_num_threads(4)
    models=ASSETS/'models';models.mkdir(parents=True,exist_ok=True)
    ocr_hub.MODEL_CACHE_DIR=models/'ocr';detector_hub.MODEL_CACHE_DIR=models/'plate'
    opts=ort.SessionOptions();opts.intra_op_num_threads=4;opts.inter_op_num_threads=1
    alpr=ALPR(detector_model='yolo-v9-t-384-license-plate-end2end',ocr_model='cct-s-v2-global-model',detector_providers=['CPUExecutionProvider'],ocr_providers=['CPUExecutionProvider'],detector_sess_options=opts,ocr_sess_options=opts)
    yolo=YOLO(str(models/'yolov8n.pt'))
    versions={name:importlib.metadata.version(name) for name in ['fast-alpr','fast-plate-ocr','open-image-models','ultralytics','onnxruntime','torch']}
    metadata={'vehicle':'yolov8n.pt','plate':'yolo-v9-t-384-license-plate-end2end','ocr':'cct-s-v2-global-model','provider':'CPUExecutionProvider','versions':versions}
    (models/'manifest.json').write_text(json.dumps(metadata,indent=2))
    _models=(yolo,alpr,metadata)
    return _models

def infer_image(path,output_dir=None):
    yolo,alpr,metadata=load_models()
    started=time.perf_counter()
    from PIL import Image
    import cv2
    image=ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    w,h=image.size
    if w*h>40_000_000: raise ValueError('Image exceeds the 40 megapixel processing limit.')
    frame=np.asarray(image)[:,:,::-1].copy()
    results=yolo.predict(frame,classes=[2,3,5,7],conf=.25,imgsz=960,verbose=False,device='cpu')[0]
    vehicles=[]
    if results.boxes is not None:
        for box in results.boxes:
            coords=box.xyxy[0].cpu().numpy().astype(int).tolist()
            coords=[max(0,coords[0]),max(0,coords[1]),min(w,coords[2]),min(h,coords[3])]
            vehicles.append({'box':coords,'confidence':float(box.conf[0]),'type':{2:'car',3:'motorcycle',5:'bus',7:'truck'}.get(int(box.cls[0]),'unknown')})
    found=[]
    # Plate detection remains useful when the generic vehicle detector misses a vehicle.
    regions=vehicles[:12] if vehicles else [{'box':[0,0,w,h],'confidence':None,'type':'unknown'}]
    for v in regions:
        x1,y1,x2,y2=v['box'];crop=frame[y1:y2,x1:x2]
        if crop.size==0:continue
        predictions=alpr.predict(crop)
        if not predictions:
            found.append({'raw_plate':None,'ocr_confidence':None,'plate_confidence':None,'plate_box':None,'character_scores':None,'vehicle_box':v['box'] if v['confidence'] is not None else None,'vehicle_confidence':v['confidence'],'vehicle_type':v['type'],'color':'unknown'})
        for p in predictions:
            b=p.detection.bounding_box;pb=[max(0,x1+b.x1),max(0,y1+b.y1),min(w,x1+b.x2),min(h,y1+b.y2)]
            scores=p.ocr.confidence if p.ocr else None
            text=(p.ocr.text or '').strip() if p.ocr else ''
            confidence=(float(np.mean(scores)) if isinstance(scores,(list,np.ndarray)) else (float(scores) if scores is not None else None)) if text else None
            found.append({'raw_plate':text or None,'ocr_confidence':confidence,'character_scores':[float(x) for x in scores] if text and isinstance(scores,(list,np.ndarray)) else None,'plate_confidence':float(p.detection.confidence),'plate_box':pb,'vehicle_box':v['box'] if v['confidence'] is not None else None,'vehicle_confidence':v['confidence'],'vehicle_type':v['type'],'color':'unknown'})
    found=deduplicate_detections(found)
    elapsed=time.perf_counter()-started
    folder=Path(output_dir) if output_dir else EVIDENCE
    folder.mkdir(parents=True,exist_ok=True)
    stem=uuid.uuid4().hex
    original=folder/f'{stem}-original.jpg';image.save(original,quality=95)
    for i,item in enumerate(found):
        for kind in ['plate','vehicle']:
            box=item[kind+'_box'];item[kind+'_path']=None
            if box and box[2]>box[0] and box[3]>box[1]:
                file=folder/f'{stem}-{i}-{kind}.jpg';image.crop(box).save(file,quality=97);item[kind+'_path']=str(file)
        item['original_path']=str(original);item['width']=w;item['height']=h
        item['sha256']=hashlib.sha256(original.read_bytes()).hexdigest()
    return {'detections':found,'duration_seconds':round(elapsed,3),'models':metadata,'input_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'width':w,'height':h}

def fuse_readings(readings):
    """Consensus only across independently captured, explicitly grouped frames."""
    from .service import normalize_plate
    unique={r['frame_sha256']:r for r in readings}
    votes={}
    for r in unique.values():
        plate=normalize_plate(r.get('raw_plate'))
        if plate:votes[plate]=votes.get(plate,0)+1
    if not votes:return {'plate':None,'distinct_frames':len(unique),'support_ratio':0}
    ranked=sorted(votes.items(),key=lambda x:(-x[1],x[0]))
    tied=len(ranked)>1 and ranked[0][1]==ranked[1][1]
    return {'plate':None if tied else ranked[0][0],'distinct_frames':len(unique),'support_ratio':ranked[0][1]/len(unique),'tied':tied}

if __name__=='__main__':
    import sys
    if len(sys.argv)>1:
        print(json.dumps(infer_image(sys.argv[1]),indent=2))
    else:load_models();print('All model weights are cached locally.')
