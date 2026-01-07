import argparse
from ultralytics import YOLO


def main(args):

    # Load model
    model = YOLO(args.weights)

    # Validate the model
    results = model.val(data=args.data, project=args.project, split="test")

    print(f"\nValidation Results:")
    print(f"mAP50: {results.box.map50:.4f}")
    print(f"mAP50-95: {results.box.map:.4f}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validate YOLO model')
    parser.add_argument('--weights',
                        type=str,
                        required=True,
                        help='Path to model weights file')
    parser.add_argument('--data',
                        type=str,
                        required=True,
                        help='Path to dataset YAML file')
    parser.add_argument('--project',
                        type=str,
                        default='runs/val',
                        help='Project directory to save results')
    args = parser.parse_args()

    main(args)
