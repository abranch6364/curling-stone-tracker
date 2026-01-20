import argparse
import requests
import os


def main(args):
    #Send request to server to add folder to dataset
    datasets = requests.get(f"{args.server_url}/api/dataset_headers").json()
    print("Available datasets:")
    for idx, dataset in enumerate(datasets):
        print(f"{idx}: {dataset['name']}")
    dataset_index = input("Enter the index of the dataset to add to: ")

    response = requests.post(f"{args.server_url}/api/add_image_to_dataset")

    num_uploaded = 0
    num_failed = 0
    #iterate over all files in the input directory recursively if args.recursive is True, otherwise only the top directory
    for root, dirs, files in os.walk(args.input_path):
        for file in files:
            file_path = os.path.join(root, file)
            if not file.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
            with open(file_path, 'rb') as f:
                files_to_upload = {'file': (file, f, 'image/png')}

                # Requests automatically prepares a multipart/form-data request
                response = requests.post(
                    f"{args.server_url}/api/add_image_to_dataset",
                    data={
                        "dataset_name": datasets[int(dataset_index)]['name'],
                    },
                    files=files_to_upload)
                if response.status_code != 201:
                    print(f"Failed to upload {file_path}: {response.text}")
                    num_failed += 1
                else:
                    print(f"Successfully uploaded {file_path}")
                    num_uploaded += 1
        #If not recursive, break after the first iteration
        if not args.recursive:
            break

    print(f"Uploaded {num_uploaded} images, {num_failed} failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
        "Add all images in a folder structure to the dataset via the server api."
    )
    parser.add_argument("input_path",
                        type=str,
                        help="Path to the input directory")

    parser.add_argument("--server-url",
                        type=str,
                        default="http://localhost:5000",
                        help="URL of the server to get camera setups")
    parser.add_argument("-r",
                        "--recursive",
                        action="store_true",
                        help="Recursively add images from subdirectories")

    args = parser.parse_args()
    main(args)
