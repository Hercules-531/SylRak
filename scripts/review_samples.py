from PIL import Image,ImageOps,ImageDraw
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1];out=root/'artifacts'/'qa'/'samples';out.mkdir(parents=True,exist_ok=True)
manifest=json.loads((root/'assets'/'samples'/'manifest.json').read_text());batch=json.loads((root/'artifacts'/'recognition'/'batch.json').read_text())
for page in range(6):
    sheet=Image.new('RGB',(1400,1250),'#edf0f3');draw=ImageDraw.Draw(sheet)
    for j,sample in enumerate(manifest['samples'][page*10:(page+1)*10]):
        x=(j%2)*700;y=(j//2)*250
        image=ImageOps.exif_transpose(Image.open(root/'assets'/'samples'/sample['filename'])).convert('RGB');thumb=ImageOps.contain(image,(340,215));sheet.paste(thumb,(x,y+25))
        draw.text((x+5,y+5),sample['id']+' / '+sample['original_filename'].split('/')[-1],fill='black')
        predictions=batch.get(sample['id'],{}).get('detections',[])
        boxes=sorted([d for d in predictions if d.get('plate_box')],key=lambda d:(d['plate_box'][2]-d['plate_box'][0])*(d['plate_box'][3]-d['plate_box'][1]),reverse=True)
        for k,d in enumerate(boxes[:3]):
            crop=ImageOps.contain(image.crop(d['plate_box']),(325,65));sheet.paste(crop,(x+350,y+30+k*70))
    sheet.save(out/f'review-{page+1}.jpg')
print(out)
