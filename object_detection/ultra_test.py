from ultralytics import YOLO
from ultralytics import settings
import torch
def main():
    torch.cuda.empty_cache()

    print("Training complete. Starting evaluation...")
    test_model = YOLO("./runs/detect/train3/weights/best.pt")

    results = test_model.val(data="./data/curling_stone_topdown.yaml", split="test")
    print(results)

if __name__ == '__main__':
    main()