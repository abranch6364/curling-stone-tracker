from ultralytics import YOLO
from ultralytics import settings
import torch
import yaml
import argparse


def main(args):
    torch.cuda.empty_cache()
    settings.update({'tensorboard': True})

    # Load hyperparameters if provided
    hyp = None
    if args.hyp:
        with open(args.hyp, 'r') as f:
            hyp = yaml.safe_load(f)

    # Train YOLO model
    model = YOLO(args.model)

    train_kwargs = {
        'data': args.data,
        'epochs': args.epochs,
        'batch': args.batch,
        'device': args.device,
        'project': args.project,
    }

    if hyp:
        train_kwargs.update(hyp)

    model.train(**train_kwargs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train YOLO model')
    parser.add_argument('--data',
                        type=str,
                        required=True,
                        help='Path to data YAML file')
    parser.add_argument('--epochs',
                        type=int,
                        default=50,
                        help='Number of training epochs')
    parser.add_argument('--batch', type=int, default=8, help='Batch size')
    parser.add_argument('--model',
                        type=str,
                        default='yolov9s.pt',
                        help='YOLO model config/weights')
    parser.add_argument('--device', type=int, default=0, help='CUDA device ID')
    parser.add_argument('--project',
                        type=str,
                        default='runs',
                        help='Project directory for saving results')
    parser.add_argument('--hyp',
                        type=str,
                        default=None,
                        help='Path to hyperparameters YAML file')

    args = parser.parse_args()

    main(args)
