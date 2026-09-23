"""Evaluate the shipped pipeline; retain predictions before loading reference text."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.inference import infer_image,box_iou
from scripts.benchmark_recognition import principal,norm,distance
OUT=ROOT/'artifacts/recognition-upgrade';OUT.mkdir(exist_ok=True,parents=True)
manifest=json.loads((ROOT/'assets/samples/manifest.json').read_text())['samples']
boxes=json.loads((OUT/'plate-boxes.json').read_text());rows=[];tp=fp=fn=0;matched=[]
demo_groups={x.get('vehicle_group') for x in manifest if x.get('split')=='demo'};seen=set()
for sample in manifest:
    if sample.get('split')!='evaluation' or sample['sha256'] in seen or sample.get('vehicle_group') in demo_groups:continue
    seen.add(sample['sha256'])
    result=infer_image(ROOT/'assets/samples'/sample['filename'],OUT/'release-crops')
    selected=principal(result['detections']);predicted=norm(selected.get('raw_plate'))
    truth=norm(sample['ground_truth']);annotation=boxes.get(sample['id']);spatial=None
    if annotation:
        candidates=[d for d in result['detections'] if d.get('plate_box')];used=set()
        for d in sorted(candidates,key=lambda d:d['plate_confidence'],reverse=True):
            ranked=sorted(((box_iou(d['plate_box'],b),i) for i,b in enumerate(annotation) if i not in used),reverse=True)
            if ranked and ranked[0][0]>=.5:tp+=1;used.add(ranked[0][1])
            else:fp+=1
        fn+=len(annotation)-len(used)
        # Principal reference plate is the largest annotated plate, independently of its text.
        target=max(annotation,key=lambda b:(b[2]-b[0])*(b[3]-b[1]))
        closest=max(candidates,key=lambda d:box_iou(d['plate_box'],target),default=None)
        spatial=norm(closest['raw_plate']) if closest and box_iou(closest['plate_box'],target)>=.5 else ''
        from backend import inference
        from backend.recognition_options import prepare_crop,single_line
        from PIL import Image,ImageOps
        import numpy as np
        frame=np.asarray(ImageOps.exif_transpose(Image.open(ROOT/'assets/samples'/sample['filename'])).convert('RGB'))[:,:,::-1].copy()
        crop_text,_=inference._paddle.read(single_line(prepare_crop(frame,target)))
        matched.append({'sample':sample['id'],'truth':truth,'spatial_prediction':spatial,'annotated_crop_prediction':norm(crop_text),'detected':bool(closest and box_iou(closest['plate_box'],target)>=.5)})
    rows.append({'sample':sample['id'],'truth':truth,'prediction':predicted,'exact':predicted==truth,
                 'edit_distance':distance(truth,predicted),'seconds':result['duration_seconds']})
    print(sample['id'],predicted,flush=True)
report={'model':result['models'],'images':len(rows),'exact':sum(r['exact'] for r in rows),
    'exact_accuracy':sum(r['exact'] for r in rows)/len(rows),'cer':sum(r['edit_distance'] for r in rows)/sum(len(r['truth']) for r in rows),
    'unreadable':sum(not r['prediction'] for r in rows),'mean_inference_seconds':sum(r['seconds'] for r in rows)/len(rows),
    'plate_detection':{'annotated_images':len(matched),'iou':.5,'tp':tp,'fp':fp,'fn':fn,'precision':tp/max(1,tp+fp),'recall':tp/max(1,tp+fn)},
    'spatial_full_plate':{'n':len(matched),'exact':sum(r['truth']==r['spatial_prediction'] for r in matched)},
    'ocr_annotated_crops':{'n':len(matched),'exact':sum(r['truth']==r['annotated_crop_prediction'] for r in matched)},
    'limitations':['Exploratory convenience set, previously inspected; not an untouched test set.','Bounding boxes exist for only four non-demo evaluation images; detection statistics are illustrative only.','Vehicle detection precision/recall unavailable: no vehicle box annotations.','No 90% claim. Fine-tuning and 200 independent test images remain outstanding.'],
    'rows':rows,'spatial_rows':matched}
(OUT/'release-evaluation.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['rows','spatial_rows','model']},indent=2))
