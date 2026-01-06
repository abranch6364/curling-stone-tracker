import argparse
import yaml
import os
import random


def main(args):
    with open(args.input_file, 'r') as f:
        yaml_data = yaml.safe_load(f)

    filenames = [
        entry.name
        for entry in os.scandir(os.path.join(yaml_data["path"], "images"))
        if entry.is_file()
    ]

    train_size = int(len(filenames) * args.train_ratio)
    val_size = int(len(filenames) * args.val_ratio)

    random.shuffle(filenames)
    training = filenames[:train_size]
    validation = filenames[train_size:train_size + val_size]
    testing = filenames[train_size + val_size:]

    output_prefix = "./images/"
    os.makedirs(yaml_data["path"], exist_ok=True)

    with open(os.path.join(yaml_data["path"], "train.txt"), 'w') as f:
        for item in training:
            f.write(f"{output_prefix}{item}\n")

    with open(os.path.join(yaml_data["path"], "val.txt"), 'w') as f:
        for item in validation:
            f.write(f"{output_prefix}{item}\n")

    with open(os.path.join(yaml_data["path"], "test.txt"), 'w') as f:
        for item in testing:
            f.write(f"{output_prefix}{item}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Split a dataset into training and validation sets.")
    parser.add_argument("input_file",
                        type=str,
                        help="Path to the yaml file defining the dataset.")

    parser.add_argument("--train-ratio",
                        type=float,
                        default=0.7,
                        help="Proportion of data to be used for training.")

    parser.add_argument("--val-ratio",
                        type=float,
                        default=0.1,
                        help="Proportion of data to be used for validation.")

    args = parser.parse_args()

    main(args)
