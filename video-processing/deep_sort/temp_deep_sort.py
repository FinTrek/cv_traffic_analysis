
import numpy as np
import torch

# Changed the relative paths to access libraries
from deep_sort.deep.feature_extractor import Extractor
from deep_sort.sort.nn_matching import NearestNeighborDistanceMetric
from deep_sort.sort.preprocessing import non_max_suppression
from deep_sort.sort.detection import Detection
from deep_sort.sort.tracker import Tracker


__all__ = ['DeepSort']


#-----------------------------------------------------------------------------------------
# ORIGIANL CODE


class DeepSort(object):
    def __init__(self, model_path, max_dist=0.2, min_confidence=0.3, nms_max_overlap=1.0, max_iou_distance=0.7, max_age=70, n_init=3, nn_budget=100, use_cuda=True):
        self.min_confidence = min_confidence
        self.nms_max_overlap = nms_max_overlap
        
        self.extractor = Extractor(model_path, use_cuda=use_cuda)
        
        max_cosine_distance = max_dist
        nn_budget = 100
        metric = NearestNeighborDistanceMetric("cosine", max_cosine_distance, nn_budget)
        self.tracker = Tracker(metric, max_iou_distance=max_iou_distance, max_age=max_age, n_init=n_init)
        
    def update(self, bbox_xywh, confidences, detected_classes, ori_img):
        self.height, self.width = ori_img.shape[:2]
        # generate detections
        features = self._get_features(bbox_xywh, ori_img)
        bbox_tlwh = self._xywh_to_tlwh(bbox_xywh)
        detections = [Detection(bbox_tlwh[i], conf, detected_classes[i], features[i]) for i,conf in enumerate(confidences) if conf>self.min_confidence]
        
        # run on non-maximum supression
        boxes = np.array([d.tlwh for d in detections])
        scores = np.array([d.confidence for d in detections])
        indices = non_max_suppression(boxes, self.nms_max_overlap, scores)
        detections = [detections[i] for i in indices]
        
        # update tracker
        self.tracker.predict()
        self.tracker.update(detections)
        
        # output bbox identities
        outputs = []
        for track in self.tracker.tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue
            box = track.to_tlwh()
            x1,y1,x2,y2 = self._tlwh_to_xyxy(box)
            track_id = track.track_id
            outputs.append(np.array([x1,y1,x2,y2,track_id], dtype=np.int))
        if len(outputs) > 0:
            outputs = np.stack(outputs,axis=0)
        
        # Add confidences
        outputs = np.append(outputs, np.expand_dims(confidences, axis=0).transpose(), axis=1)
        
        # Add detection classes
        outputs = np.append(outputs, np.expand_dims(detected_classes, axis=0).transpose(), axis=1)
        
        return outputs
    
    
    """
    TODO:
        Convert bbox from xc_yc_w_h to xtl_ytl_w_h
    Thanks JieChen91@github.com for reporting this bug!
    """
    @staticmethod
    def _xywh_to_tlwh(bbox_xywh):
        if isinstance(bbox_xywh, np.ndarray):
            bbox_tlwh = bbox_xywh.copy()
        elif isinstance(bbox_xywh, torch.Tensor):
            bbox_tlwh = bbox_xywh.clone()
        bbox_tlwh[:,0] = bbox_xywh[:,0] - bbox_xywh[:,2]/2.
        bbox_tlwh[:,1] = bbox_xywh[:,1] - bbox_xywh[:,3]/2.
        return bbox_tlwh
    
    def _xywh_to_xyxy(self, bbox_xywh):
        x,y,w,h = bbox_xywh
        x1 = max(int(x-w/2),0)
        x2 = min(int(x+w/2),self.width-1)
        y1 = max(int(y-h/2),0)
        y2 = min(int(y+h/2),self.height-1)
        return x1,y1,x2,y2
    
    def _tlwh_to_xyxy(self, bbox_tlwh):
        """
        TODO:
            Convert bbox from xtl_ytl_w_h to xc_yc_w_h
        Thanks JieChen91@github.com for reporting this bug!
        """
        x,y,w,h = bbox_tlwh
        x1 = max(int(x),0)
        x2 = min(int(x+w),self.width-1)
        y1 = max(int(y),0)
        y2 = min(int(y+h),self.height-1)
        return x1,y1,x2,y2
    
    def _xyxy_to_tlwh(self, bbox_xyxy):
        x1,y1,x2,y2 = bbox_xyxy
        
        t = x1
        l = y1
        w = int(x2-x1)
        h = int(y2-y1)
        return t,l,w,h
    
    def _get_features(self, bbox_xywh, ori_img):
        im_crops = []
        for box in bbox_xywh:
            x1,y1,x2,y2 = self._xywh_to_xyxy(box)
            im = ori_img[y1:y2,x1:x2]
            im_crops.append(im)
        if im_crops:
            features = self.extractor(im_crops)
        else:
            features = np.array([])
        return features


#-----------------------------------------------------------------------------------------
# DRAFT

# Create isntance
S = DeepSort(cfg.DEEPSORT.REID_CKPT, 
                max_dist=cfg.DEEPSORT.MAX_DIST, min_confidence=cfg.DEEPSORT.MIN_CONFIDENCE, 
                nms_max_overlap=cfg.DEEPSORT.NMS_MAX_OVERLAP, max_iou_distance=cfg.DEEPSORT.MAX_IOU_DISTANCE, 
                max_age=cfg.DEEPSORT.MAX_AGE, n_init=cfg.DEEPSORT.N_INIT, nn_budget=cfg.DEEPSORT.NN_BUDGET, use_cuda=False)

# Expore update method update()

# from yelov3_deepsort.py: outputs = self.deepsort.update(bbox_xywh, cls_conf, im)
bbox_xywh = vdo_trk.detections[0]
confidences =  vdo_trk.detections[1]
detected_classes = vdo_trk.detections[2]
ori_img = vdo_trk.im

# def update(self, bbox_xywh, confidences, ori_img):
S.height, S.width = ori_img.shape[:2]
# generate detections
features = S._get_features(bbox_xywh, ori_img)
bbox_tlwh = S._xywh_to_tlwh(bbox_xywh)
detections = [Detection(bbox_tlwh[i], conf, features[i], detected_classes[i]) for i,conf in enumerate(confidences) if conf>S.min_confidence]


# run on non-maximum supression
boxes = np.array([d.tlwh for d in detections])
scores = np.array([d.confidence for d in detections])
indices = non_max_suppression(boxes, S.nms_max_overlap, scores)
detections = [detections[i] for i in indices]

# update tracker
S.tracker.predict()
S.tracker.update(detections)

# output bbox identities
outputs = []
for track in S.tracker.tracks:
    # if not track.is_confirmed() or track.time_since_update > 1:
    #     continue
    box = track.to_tlwh()
    x1,y1,x2,y2 = S._tlwh_to_xyxy(box)
    track_id = track.track_id
    track_class_id = track.class_id
    outputs.append(np.array([x1,y1,x2,y2,track_id, track_class_id], dtype=np.int))

if len(outputs) > 0:
    outputs = np.stack(outputs,axis=0)

# Add confidences
outputs = np.append(outputs, np.expand_dims(confidences, axis=0).transpose(), axis=1)

# Add detection classes
outputs = np.append(outputs, np.expand_dims(detected_classes, axis=0).transpose(), axis=1)

for track in S.tracker.tracks:
    print(track.class_id)

