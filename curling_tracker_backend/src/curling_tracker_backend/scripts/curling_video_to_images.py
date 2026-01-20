import argparse
import cv2 as cv
import os
import requests
import curling_tracker_backend.util.async_yt_dlp as async_yt_dlp
import curling_tracker_backend.util.curling_shot_tracker as shot_tracker
import tqdm


def sanitize_camera_name(name: str) -> str:
    return name.replace(" ", "_").replace("/", "_")


def main(args):

    #Send request to server to get camera setups
    camera_setup_headers = requests.get(
        f"{args.server_url}/api/camera_setup_headers").json()

    print("Available camera views:")
    for idx, camera in enumerate(camera_setup_headers):
        print(f"{idx}: {camera['setup_name']}")

    setup_index = input("Enter the index of the camera setup to use: ")

    camera_setup = requests.get(
        f"{args.server_url}/api/camera_setup",
        params={
            "setup_id": camera_setup_headers[int(setup_index)]["setup_id"]
        }).json()
    print(f"Selected camera setup: {camera_setup['setup_name']}")

    #Ask for what camera views to save
    print("Available camera views in the selected setup:")
    for idx, camera in enumerate(camera_setup["cameras"]):
        print(f"{idx}: {camera['camera_name']}")
    camera_indices = input(
        "Enter the indices of the camera views to extract images from (comma separated): "
    )
    camera_indices = [int(idx) for idx in camera_indices.split(",")]

    if args.video_url == "":
        video_url = input("Enter the url of the video to use: ")
    else:
        video_url = args.video_url

    #Create output directories for each camera view
    os.makedirs(args.output_path, exist_ok=True)
    for cam_idx in camera_indices:
        camera = camera_setup["cameras"][cam_idx]
        cam_output_path = os.path.join(
            args.output_path, sanitize_camera_name(camera["camera_name"]))
        os.makedirs(cam_output_path, exist_ok=True)

    print("Downloading video...")
    async_yt_dlp.download_video_sync(url=video_url,
                                     output_path=os.path.join(
                                         args.output_path, "temp_video.mp4"),
                                     start_time=args.start_second,
                                     end_time=args.end_second)

    video = shot_tracker.CurlingVideo(
        video_path=os.path.join(args.output_path, "temp_video.mp4"))

    for idx, frame in tqdm.tqdm(
            video.frame_generator(second_interval=args.interval),
            total=video.num_frames // (video.fps * args.interval)):
        for cam_idx in camera_indices:
            camera_dict = camera_setup["cameras"][cam_idx]
            camera = shot_tracker.Camera(
                camera_dict["camera_name"],
                camera_dict["corner1"],
                camera_dict["corner2"],
                camera_dict["camera_matrix"],
                camera_dict["distortion_coefficients"],
                camera_dict["rotation_vectors"],
                camera_dict["translation_vectors"],
            )
            sanitized_camera_name = sanitize_camera_name(
                camera_dict["camera_name"])
            split_frame = camera.extract_image(frame)

            output_filename = os.path.join(
                args.output_path,
                sanitized_camera_name,
                f"{args.output_prefix}{sanitized_camera_name}_{idx:06d}.png",
            )
            cv.imwrite(output_filename, split_frame)

    if args.delete_temp:
        os.remove(os.path.join(args.output_path, "temp_video.mp4"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
        "Download a video from youtube, extract frames at intervals, split by camera view, and save as images."
    )
    parser.add_argument("output_path",
                        type=str,
                        help="Path to the output directory")
    parser.add_argument("--video-url",
                        default="",
                        type=str,
                        help="URL of the video to extract images from")
    parser.add_argument("--interval",
                        type=int,
                        default=1,
                        help="Interval in seconds between extracted frames")
    parser.add_argument("--output-prefix",
                        type=str,
                        default="",
                        help="Prefix for output image files")
    parser.add_argument("--start-second",
                        type=int,
                        help="Start extracting frames from this second")
    parser.add_argument("--end-second",
                        type=int,
                        help="Stop extracting frames at this second")

    parser.add_argument("--server-url",
                        type=str,
                        default="http://localhost:5000",
                        help="URL of the server to get camera setups")
    parser.add_argument("-d",
                        "--delete-temp",
                        action="store_true",
                        help="Delete temporary video file after processing")

    args = parser.parse_args()
    main(args)
