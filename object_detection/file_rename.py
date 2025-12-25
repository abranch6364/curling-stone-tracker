import os

directory_path = "C:\\Users\\abran\\Desktop\\curling_dataset_temp\\top_down_b"  # Replace with your directory path

for i, filename in enumerate(os.listdir(directory_path)):
    full_path = os.path.join(directory_path, filename)
    if os.path.isfile(full_path):  # Check if it's actually a file
        os.rename(full_path, os.path.join(directory_path, f"top_down_b_nov_13_{i:06d}.png"))