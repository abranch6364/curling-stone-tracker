import argparse
import curling_tracker_backend.util.curling_image_processing as cip
import cv2 as cv
import os


def main():
    """Main function for this script which takes in a video and outputs frames as images."""

    parser = argparse.ArgumentParser(
        description="Extract images from a curling video.")
    parser.add_argument("video_path",
                        type=str,
                        help="Path to the input video file")
    parser.add_argument("output_path",
                        type=str,
                        help="Path to the output directory")
    parser.add_argument("--interval",
                        type=int,
                        default=1,
                        help="Interval in seconds between extracted frames")
    parser.add_argument("--output-prefix",
                        type=str,
                        default="frame",
                        help="Prefix for output image files")
    parser.add_argument("--start-second",
                        type=int,
                        default=0,
                        help="Start extracting frames from this second")
    parser.add_argument("--split",
                        type=bool,
                        default=False,
                        help="Split each image into the individual cameras")

    args = parser.parse_args()

    output_path = args.output_path

    if args.split:
        os.mkdir(f"{output_path}/top_down_a")
        os.mkdir(f"{output_path}/top_down_b")
        os.mkdir(f"{output_path}/angled_a")
        os.mkdir(f"{output_path}/angled_b")

    for count, image in cip.extract_images_from_video(
            args.video_path,
            second_interval=args.interval,
            start_second=args.start_second):
        if args.split:
            top_down_a, top_down_b, angled_a, angled_b = cip.split_stream_frame(
                image)
            cv.imwrite(
                f"{output_path}/top_down_a/{args.output_prefix}{count:06d}.png",
                top_down_a)
            cv.imwrite(
                f"{output_path}/top_down_b/{args.output_prefix}{count:06d}.png",
                top_down_b)
            cv.imwrite(
                f"{output_path}/angled_a/{args.output_prefix}{count:06d}.png",
                angled_a)
            cv.imwrite(
                f"{output_path}/angled_b/{args.output_prefix}{count:06d}.png",
                angled_b)
        else:
            cv.imwrite(f"{output_path}/{args.output_prefix}{count:06d}.png",
                       image)


if __name__ == "__main__":
    main()
