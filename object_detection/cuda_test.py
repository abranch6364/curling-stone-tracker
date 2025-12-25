import torch

# Check if CUDA is available
if torch.cuda.is_available():
    print("CUDA is available!")
    # Get the number of available GPUs
    num_gpus = torch.cuda.device_count()
    print(f"Number of GPUs available: {num_gpus}")

    # List details for each GPU
    for i in range(num_gpus):
        print(f"--- GPU {i} ---")
        print(f"Device Name: {torch.cuda.get_device_name(i)}")
        print(f"Current Device: {torch.cuda.current_device() == i}")
else:
    print("CUDA is not available. PyTorch will use the CPU.")
