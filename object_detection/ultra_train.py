from ultralytics import YOLO
from ultralytics import settings
import torch
def main():
    torch.cuda.empty_cache()

    settings.update({'tensorboard': True})

    # Your YOLO training code goes here
    model = YOLO("yolov9m.pt")
    model.train(data="./data/curling_stone_topdown.yaml", epochs=10, imgsz=519, batch=8, rect=True, device=0)

if __name__ == '__main__':
    main()