import optuna
from ultralytics import YOLO
import yaml
import argparse
from functools import partial
import torch
from ultralytics import settings


def get_train_args(defaults):
    """Load default training arguments from YAML file."""
    with open(defaults, 'r') as f:
        train_args = yaml.safe_load(f)
    return train_args if train_args else {}


def objective(train_args, yolo_model, trial):
    """Objective function for Optuna hyperparameter tuning."""

    # Suggest hyperparameters
    train_args["lr0"] = trial.suggest_float('lr0', 1e-5, 1e-1, log=True)
    train_args["lrf"] = trial.suggest_float('lrf', 0.01, 1.0)
    train_args["momentum"] = trial.suggest_float('momentum', 0.6, 0.98)
    train_args["weight_decay"] = trial.suggest_float('weight_decay', 0.0,
                                                     0.001)
    train_args["warmup_epochs"] = trial.suggest_int('warmup_epochs', 0, 5)
    train_args["box"] = trial.suggest_float('box', 1.0, 10.0)
    train_args["cls"] = trial.suggest_float('cls', 0.2, 2.0)

    train_args["name"] = f'trial_{trial.number}'
    train_args["verbose"] = False

    # Load model
    model = YOLO(yolo_model)

    # Train with suggested hyperparameters
    results = model.train(**train_args)

    # Return metric to optimize (e.g., mAP50-95)
    return results.results_dict['metrics/mAP50-95(B)']


def main(args):
    """Run hyperparameter tuning with Optuna."""
    torch.cuda.empty_cache()
    settings.update({'tensorboard': True})

    # Create study
    study = optuna.create_study(
        direction='maximize',
        study_name='yolo_tuning',
        storage='sqlite:////docker_data/yolo_tuning.db',
        load_if_exists=True)

    train_args = get_train_args(args.defaults)
    train_args["data"] = args.data
    train_args["epochs"] = args.epochs
    train_args["batch"] = args.batch
    train_args["project"] = args.project
    train_args["optimizer"] = 'AdamW'

    # Optimize
    study.optimize(partial(objective, train_args, args.model),
                   n_trials=args.trials)

    # Print results
    print('Best trial:')
    trial = study.best_trial
    print(f'  Value (mAP50-95): {trial.value:.4f}')
    print('  Params:')
    for key, value in trial.params.items():
        print(f'    {key}: {value}')

    # Save best hyperparameters
    with open(args.output, 'w') as f:
        yaml.dump(trial.params, f)

    print(f'\nBest hyperparameters saved to {args.output}')
    yaml.dump(trial.params, f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='YOLO hyperparameter tuning with Optuna')

    parser.add_argument(
        '--defaults',
        type=str,
        default='default_hyperparameters.yaml',
        help=
        'Path to default hyperparameters YAML file (default: default_hyperparameters.yaml)'
    )
    parser.add_argument('--data',
                        type=str,
                        default='data.yaml',
                        help='Path to data YAML file (default: data.yaml)',
                        required=True)

    parser.add_argument('--batch',
                        type=int,
                        default=8,
                        help='Batch size for training (default: 8)')
    parser.add_argument('--epochs',
                        type=int,
                        default=50,
                        help='Number of epochs for training (default: 50)')
    parser.add_argument('--model',
                        type=str,
                        default='yolov8s.pt',
                        help='Path to YOLO model (default: yolov8s.pt)',
                        required=True)
    parser.add_argument(
        '--project',
        type=str,
        default='runs/tune',
        help='Project directory for saving results (default: runs/tune)')
    parser.add_argument('--trials',
                        type=int,
                        default=20,
                        help='Number of Optuna trials (default: 20)')
    parser.add_argument(
        '--output',
        type=str,
        default='best_hyperparameters.yaml',
        help=
        'Path to save best hyperparameters (default: best_hyperparameters.yaml)'
    )
    args = parser.parse_args()

    main(args)
