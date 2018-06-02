import os
import sys
import random
import math
import numpy as np
import tensorflow as tf

import coco
import utils
import model as modellib


def load_mask_rcnn():

    ROOT_DIR = os.getcwd()

    MODEL_DIR = os.path.join(ROOT_DIR, "logs")

    COCO_MODEL_PATH = os.path.join(ROOT_DIR, "mask_rcnn_coco.h5")

    if not os.path.exists(COCO_MODEL_PATH):
        utils.download_trained_weights(COCO_MODEL_PATH)

    class InferenceConfig(coco.CocoConfig):

        GPU_COUNT = 1
        IMAGES_PER_GPU = 1

    config = InferenceConfig()
    config.display()

    DEVICE= "/cpu:0"
    with tf.device(DEVICE):
        model = modellib.MaskRCNN(mode="inference", model_dir=MODEL_DIR, config=config)

    model.load_weights(COCO_MODEL_PATH, by_name=True)

    class_names = ['BG', 'person', 'bicycle', 'car', 'motorcycle', 'airplane',
                   'bus', 'train', 'truck', 'boat', 'traffic light',
                   'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird',
                   'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear',
                   'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie',
                   'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
                   'kite', 'baseball bat', 'baseball glove', 'skateboard',
                   'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
                   'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
                   'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
                   'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed',
                   'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
                   'keyboard', 'cell phone', 'microwave', 'oven', 'toaster',
                   'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors',
                   'teddy bear', 'hair drier', 'toothbrush']

    return model

def select_people(model, image):

        results = model.detect([image], verbose=1)
        r = results[0]

        indexes = np.argwhere(r['class_ids']==1)

        bbox = utils.extract_bboxes(r['masks'])

        peoples = []
        boxes = []

        for i in indexes:
            if r['scores'][i.item()] >= 0.9:

                top, left, bottom, right = bbox[i.item()]

                cropped_image = image[top:bottom, left:right]
                peoples.append(cropped_image)

                boxes.append([top, bottom, left, right])

        return peoples, boxes


if __name__ == "__main__":
    select_people('../../images', '../../extracted/')
