

import argparse
import json
import os
import random

def extract_data(input_file):
    with open(input_file, 'r') as f:
        data = json.load(f)

    image_filenames = []
    images = data['images']
    for img in images:
        image_filenames.append(os.path.basename(img['file_name']))

    return image_filenames


def main(args):
    filenames = extract_data(args.input_file)
    train_size = int(len(filenames) * args.train_ratio)
    val_size = int(len(filenames) * args.val_ratio)

    random.shuffle(filenames)
    training = filenames[:train_size]
    validation = filenames[train_size:train_size + val_size]
    testing = filenames[train_size + val_size:]

    output_prefix = "./images/"
    os.makedirs(args.output_directory, exist_ok=True)

    with open(os.path.join(args.output_directory, "train.txt"), 'w') as f:
        for item in training:
            f.write(f"{output_prefix}{item}\n")

    with open(os.path.join(args.output_directory, "val.txt"), 'w') as f:
        for item in validation:
            f.write(f"{output_prefix}{item}\n")

    with open(os.path.join(args.output_directory, "test.txt"), 'w') as f:
        for item in testing:
            f.write(f"{output_prefix}{item}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split a dataset into training and validation sets.")
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input dataset file (e.g., JSON format)."
    )

    parser.add_argument(
        "output_directory",
        type=str,
        help="Path to save the datasets."
    )

    parser.add_argument(
        "--train_ratio",
        type=float,
        default=0.7,
        help="Proportion of data to be used for training."
    )

    parser.add_argument(
        "--val_ratio",
        type=float,
        default=0.1,
        help="Proportion of data to be used for validation."
    )

    args = parser.parse_args()

    main(args)
