import argparse
import curling_image_processing as cip
import cv2 as cv
import os
def main(args):
    video_path = args.video_path
    output_path = args.output_path

    os.mkdir(f"{output_path}/top_down_a")
    os.mkdir(f"{output_path}/top_down_b")
    os.mkdir(f"{output_path}/angled_a")
    os.mkdir(f"{output_path}/angled_b")

    for count, image in cip.extract_images_from_video(video_path, second_interval=args.interval, start_second=args.start_second):
        top_down_a, top_down_b, angled_a, angled_b = cip.split_stream_frame(image)
        cv.imwrite(f"{output_path}/top_down_a/{args.output_prefix}{count:06d}.png", top_down_a)
        cv.imwrite(f"{output_path}/top_down_b/{args.output_prefix}{count:06d}.png", top_down_b)
        cv.imwrite(f"{output_path}/angled_a/{args.output_prefix}{count:06d}.png", angled_a)
        cv.imwrite(f"{output_path}/angled_b/{args.output_prefix}{count:06d}.png", angled_b)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract images from a curling video.")
    parser.add_argument("video_path", type=str, help="Path to the input video file")
    parser.add_argument("output_path", type=str, help="Path to the output directory")
    parser.add_argument("--interval", type=int, default=1, help="Interval in seconds between extracted frames")
    parser.add_argument("--output_prefix", type=str, default="frame", help="Prefix for output image files")
    parser.add_argument("--start_second", type=int, default=0, help="Start extracting frames from this second")

    args = parser.parse_args()

    main(args)