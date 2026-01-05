import argparse
import os
import zipfile
from pathlib import Path
from label_studio_sdk import Client

#!/usr/bin/env python3
"""
Utility to download and extract a dataset from Label Studio in YOLO format.
"""


def download_and_extract_dataset(api_url: str, api_key: str, project_id: int,
                                 target_dir: str):
    """
    Download dataset from Label Studio and extract to target directory.
    
    Args:
        api_url: Label Studio API URL
        api_key: API key for authentication
        project_id: Project ID to download
        target_dir: Directory to extract the dataset
    """
    # Initialize Label Studio client
    ls = Client(url=api_url, api_key=api_key)

    # Get the project
    project = ls.get_project(project_id)

    # Export dataset in YOLO format
    print(f"Exporting project {project_id} in YOLO format...")
    export_result = project.export_tasks(export_type='YOLO',
                                         download_resources=True)

    # Create target directory if it doesn't exist
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    # Save the exported file
    zip_path = target_path / f"dataset_{project_id}.zip"
    with open(zip_path, 'wb') as f:
        f.write(export_result)

    print(f"Downloaded dataset to {zip_path}")

    # Extract the zip file
    print(f"Extracting to {target_dir}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_path)

    # Remove the zip file
    os.remove(zip_path)

    print(f"Dataset extracted successfully to {target_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Download and extract Label Studio dataset in YOLO format')
    parser.add_argument(
        '--api-url',
        required=True,
        help='Label Studio API URL (e.g., http://localhost:8080)')
    parser.add_argument('--api-key',
                        required=True,
                        help='Label Studio API key')
    parser.add_argument('--project-id',
                        type=int,
                        required=True,
                        help='Project ID to download')
    parser.add_argument('--target-dir',
                        required=True,
                        help='Target directory to extract the dataset')

    args = parser.parse_args()

    download_and_extract_dataset(api_url=args.api_url,
                                 api_key=args.api_key,
                                 project_id=args.project_id,
                                 target_dir=args.target_dir)


if __name__ == '__main__':
    main()
