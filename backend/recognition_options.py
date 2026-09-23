"""Experimental crop processing. Not enabled in production without validation."""
import math
import numpy as np
import cv2

def prepare_crop(image, box, padding=.06):
    x1,y1,x2,y2=box;w=x2-x1;h=y2-y1
    crop=image[max(0,int(y1-padding*h)):min(image.shape[0],math.ceil(y2+padding*h)),
               max(0,int(x1-padding*w)):min(image.shape[1],math.ceil(x2+padding*w))].copy()
    if crop.shape[0]>crop.shape[1]*1.3:crop=cv2.rotate(crop,cv2.ROTATE_90_CLOCKWISE)
    return crop

def single_line(crop):
    """Try stacking clearly separated text rows left-to-right; otherwise retain crop."""
    h,w=crop.shape[:2]
    if w/max(h,1)>2.7 or h<24:return crop
    gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
    _,mask=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    projection=mask[:,int(.1*w):int(.9*w)].mean(axis=1)
    lo,hi=int(h*.32),int(h*.65);split=lo+int(np.argmin(projection[lo:hi]))
    if projection[split]>np.percentile(projection,35):return crop
    top=crop[:split];bottom=crop[split:]
    target=max(top.shape[0],bottom.shape[0])
    rows=[cv2.resize(row,(round(row.shape[1]*target/row.shape[0]),target)) for row in [top,bottom]]
    return np.concatenate([rows[0],np.full((target,8,3),255,np.uint8),rows[1]],axis=1)

class PaddleCropReader:
    """Publisher inference weights through Paddle's native API; no PaddleX dependency."""
    def __init__(self, folder):
        import paddle.inference as inference
        import yaml
        config=inference.Config(str(folder/'inference.json'),str(folder/'inference.pdiparams'))
        config.disable_gpu();config.set_cpu_math_library_num_threads(4)
        config.disable_glog_info();config.disable_mkldnn()
        self.predictor=inference.create_predictor(config)
        spec=yaml.safe_load((folder/'inference.yml').read_text(encoding='utf-8'))
        self.characters=['']+spec['PostProcess']['character_dict']+[' ']
    def read(self,crop):
        h,w=crop.shape[:2];width=min(320,max(1,math.ceil(48*w/h)))
        resized=cv2.resize(crop,(width,48)).astype('float32')/127.5-1
        tensor=np.zeros((1,3,48,320),dtype='float32');tensor[0,:,:,:width]=resized.transpose(2,0,1)
        handle=self.predictor.get_input_handle(self.predictor.get_input_names()[0]);handle.reshape(tensor.shape);handle.copy_from_cpu(tensor)
        self.predictor.run();prob=self.predictor.get_output_handle(self.predictor.get_output_names()[0]).copy_to_cpu()[0]
        indices=prob.argmax(axis=-1);scores=prob.max(axis=-1);text=[];confidence=[];previous=-1
        for i,score in zip(indices,scores):
            if i and i!=previous and i<len(self.characters):text.append(self.characters[i]);confidence.append(float(score))
            previous=i
        return ''.join(text),float(np.mean(confidence)) if confidence else 0
