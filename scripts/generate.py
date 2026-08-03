#!/usr/bin/env python3
"""Agnes AI - Image and Video Generation CLI (China domestic API).

API docs: https://www.agnes-ai.cn/zh-Hans/docs/overview
API Base: https://api.agnes-ai.cn/v1

Usage:
  python generate.py image --prompt "..." [--size 1K|2K|3K|4K|WxH] [--ratio 16:9]
                           [--image IMG1 [IMG2 ...]] [--model MODEL] --output path.png
  python generate.py video --prompt "..." [--duration 5] [--image IMG]
                           [--width 1152] [--height 768] [--frame-rate 24]
                           [--model MODEL] --output path.mp4

Models (user-selectable via --model, defaults recommended):
  agnes-image-2.1-flash  image, DEFAULT for text-to-image (tier sizes 1K-4K + ratio)
  agnes-image-2.0-flash  image, DEFAULT for image-to-image / multi-image (exact WxH sizes)
  agnes-video-v2.0       video (text-to-video, image-to-video, keyframes)

API key resolution order:
  1. Environment variable AGNES_API_KEY
  2. File ~/.agnes-ai/api_key
  3. File api_key next to this script
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

API_BASE = "https://api.agnes-ai.cn/v1"
API_ROOT = "https://api.agnes-ai.cn"

DEFAULT_T2I_MODEL = "agnes-image-2.1-flash"
DEFAULT_I2I_MODEL = "agnes-image-2.0-flash"
DEFAULT_VIDEO_MODEL = "agnes-video-v2.0"

VALID_RATIOS = ["1:1", "3:4", "4:3", "16:9", "9:16", "2:3", "3:2", "21:9"]
SIZE_TIERS = ["1K", "2K", "3K", "4K"]


def get_api_key():
    """Retrieve API key: env var -> ~/.agnes-ai/api_key -> script-adjacent api_key."""
    key = os.environ.get("AGNES_API_KEY")
    if key:
        return key

    key_file = os.path.expanduser("~/.agnes-ai/api_key")
    if os.path.exists(key_file):
        with open(key_file) as f:
            return f.read().strip()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_key = os.path.join(script_dir, "api_key")
    if os.path.exists(local_key):
        with open(local_key) as f:
            return f.read().strip()

    print("ERROR: AGNES_API_KEY not found.", file=sys.stderr)
    print("Configure it in one of these ways:", file=sys.stderr)
    print("  1. Environment variable AGNES_API_KEY", file=sys.stderr)
    print("  2. File ~/.agnes-ai/api_key", file=sys.stderr)
    print("  3. File " + local_key, file=sys.stderr)
    print("Get your key at https://platform.agnes-ai.cn/", file=sys.stderr)
    sys.exit(1)


def api_request(method, url, body=None):
    """Make an authenticated request to the Agnes AI API (full URL)."""
    api_key = get_api_key()

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        # Some WAFs reset connections from default python-urllib TLS/UA fingerprints
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print("API Error (" + str(e.code) + "): " + err_body, file=sys.stderr)
        sys.exit(1)


def download_file(url, output_path):
    """Download a file from URL to local path. Returns True on success."""
    print("Downloading to " + output_path + " ...")
    try:
        urllib.request.urlretrieve(url, output_path)
    except Exception as e:
        print("ERROR: Download failed: " + str(e), file=sys.stderr)
        return False
    print("Saved: " + output_path)
    return True


def report_download_failure(url, kind):
    """Tell the user the CDN is unreachable and hand over the URL."""
    print("", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(kind + " generated successfully, but the download failed:", file=sys.stderr)
    print("the CDN host is unreachable from this network (connection reset).", file=sys.stderr)
    print("Download it manually (e.g. via another network) from:", file=sys.stderr)
    print("  " + url, file=sys.stderr)
    print("=" * 60, file=sys.stderr)


def image_to_data_url(image_path):
    """Read a local image file and return a data URL (base64-encoded)."""
    mime, _ = mimetypes.guess_type(image_path)
    if mime is None:
        mime = "image/png"
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return "data:" + mime + ";base64," + data


def resolve_image(image_arg):
    """Resolve an image argument to a URL or data URI string."""
    if image_arg.startswith("http://") or image_arg.startswith("https://"):
        return image_arg
    if image_arg.startswith("data:"):
        return image_arg
    if not os.path.exists(image_arg):
        print("ERROR: Image file not found: " + image_arg, file=sys.stderr)
        sys.exit(1)
    return image_to_data_url(image_arg)


def generate_image(prompt, size, ratio, output_path, images=None, model=None):
    """Generate an image.

    Defaults: text-to-image -> agnes-image-2.1-flash (use tier size like 2K + ratio);
    image-to-image / multi-image -> agnes-image-2.0-flash (use exact WxH size).
    User can override with --model.
    """
    if images:
        selected_model = model if model else DEFAULT_I2I_MODEL
        print("Using model (image-to-image): " + selected_model)
    else:
        selected_model = model if model else DEFAULT_T2I_MODEL
        print("Using model (text-to-image): " + selected_model)

    print("Generating image: " + prompt[:80] + ("..." if len(prompt) > 80 else ""))

    body = {
        "model": selected_model,
        "prompt": prompt,
        "size": size,
    }
    if ratio:
        body["ratio"] = ratio

    # IMPORTANT (China network): image URLs in responses are hosted on
    # storage.googleapis.com, which is unreachable from domestic networks.
    # Always request base64 output so no download from that host is needed.
    # t2i uses top-level return_base64; i2i uses extra_body.response_format.
    extra_body = {"response_format": "b64_json"}
    if images:
        extra_body["image"] = [resolve_image(i) for i in images]
    else:
        body["return_base64"] = True
    body["extra_body"] = extra_body

    resp = api_request("POST", API_BASE + "/images/generations", body)

    data = resp.get("data", [])
    if not data:
        print("ERROR: No image data in response", file=sys.stderr)
        print("Full response: " + json.dumps(resp, indent=2), file=sys.stderr)
        sys.exit(1)

    item = data[0]

    if item.get("b64_json"):
        print("Decoding base64 image data...")
        img_bytes = base64.b64decode(item["b64_json"])
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        print("Saved: " + output_path)
        return output_path

    if item.get("url"):
        if download_file(item["url"], output_path):
            return output_path
        report_download_failure(item["url"], "Image")
        sys.exit(2)

    print("ERROR: No url or b64_json in image response", file=sys.stderr)
    print("Full response: " + json.dumps(resp, indent=2), file=sys.stderr)
    sys.exit(1)


def duration_to_num_frames(duration_seconds, frame_rate):
    """Convert duration to num_frames following the 8n+1 rule, clamped to <= 441."""
    raw = int(round(duration_seconds * frame_rate))
    n = max(1, round((raw - 1) / 8))
    num_frames = 8 * n + 1
    if num_frames > 441:
        num_frames = 441
    return num_frames


def generate_video(prompt, duration, output_path, image=None, width=1152, height=768,
                   frame_rate=24, negative_prompt=None, seed=None, model=None):
    """Generate a video using agnes-video-v2.0 (async task API).

    Create: POST /v1/videos
    Poll:   GET /agnesapi?video_id=<VIDEO_ID>  (recommended)
    Result URL: response.metadata.url
    """
    selected_model = model if model else DEFAULT_VIDEO_MODEL
    num_frames = duration_to_num_frames(duration, frame_rate)
    actual_seconds = round(num_frames / frame_rate, 2)

    print("Using model (video): " + selected_model)
    print("Generating video (~" + str(actual_seconds) + "s, " + str(num_frames) +
          " frames @ " + str(frame_rate) + "fps): " + prompt[:80] +
          ("..." if len(prompt) > 80 else ""))

    body = {
        "model": selected_model,
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_frames": num_frames,
        "frame_rate": frame_rate,
    }
    if image:
        body["image"] = resolve_image(image)
    if negative_prompt:
        body["negative_prompt"] = negative_prompt
    if seed is not None:
        body["seed"] = seed

    resp = api_request("POST", API_BASE + "/videos", body)

    video_id = resp.get("video_id") or resp.get("task_id") or resp.get("id")
    if not video_id:
        print("ERROR: No video_id in response", file=sys.stderr)
        print("Full response: " + json.dumps(resp, indent=2), file=sys.stderr)
        sys.exit(1)

    print("Task created. video_id: " + video_id +
          " | status: " + str(resp.get("status")) +
          " | size: " + str(resp.get("size")))

    # Poll for completion (recommended endpoint: GET /agnesapi?video_id=...)
    max_attempts = 120  # ~10 minutes at 5s intervals
    for attempt in range(max_attempts):
        time.sleep(5)
        status_resp = api_request(
            "GET", API_ROOT + "/agnesapi?video_id=" + urllib.parse.quote(video_id))

        data = status_resp.get("data", status_resp)
        if isinstance(data, dict) and "status" not in data and isinstance(data.get("data"), dict):
            data = data["data"]

        status = str(data.get("status", "unknown")).lower()
        progress = data.get("progress", "")
        print("  [" + str(attempt + 1) + "] Status: " + status +
              (" (" + str(progress) + "%)" if progress != "" else ""))

        if status in ("completed", "success"):
            metadata = data.get("metadata", {}) or {}
            url = metadata.get("url") or data.get("url") or data.get("result_url")
            if url:
                print("Output size: " + str(data.get("size")) +
                      " | seconds: " + str(data.get("seconds")))
                if download_file(url, output_path):
                    return output_path
                report_download_failure(url, "Video")
                sys.exit(2)
            print("ERROR: Completed but no video URL in metadata", file=sys.stderr)
            print("Full response: " + json.dumps(status_resp, indent=2), file=sys.stderr)
            sys.exit(1)

        if status in ("failed", "error"):
            err = data.get("error") or data.get("fail_reason") or "Unknown error"
            print("ERROR: Generation failed: " + str(err), file=sys.stderr)
            sys.exit(1)

    print("ERROR: Timed out waiting for video generation", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Agnes AI Generator (China domestic API)")
    sub = parser.add_subparsers(dest="command", required=True)

    # Image subcommand
    img = sub.add_parser("image", help="Generate an image")
    img.add_argument("--prompt", required=True, help="Image description / edit instruction")
    img.add_argument("--size", default="1K",
                     help="Size tier 1K/2K/3K/4K (recommended for agnes-image-2.1-flash) "
                          "or exact WxH like 1024x768 (for agnes-image-2.0-flash). Default: 1K")
    img.add_argument("--ratio", default=None,
                     help="Aspect ratio for tier sizes: " + ", ".join(VALID_RATIOS) +
                          " (server default: 1:1)")
    img.add_argument("--image", nargs="+", default=None,
                     help="Input image URL(s) or local path(s) for image-to-image / multi-image")
    img.add_argument("--model", default=None,
                     help="Override model (default: agnes-image-2.1-flash for text-to-image, "
                          "agnes-image-2.0-flash for image-to-image)")
    img.add_argument("--output", required=True, help="Output file path")

    # Video subcommand
    vid = sub.add_parser("video", help="Generate a video")
    vid.add_argument("--prompt", required=True, help="Video description")
    vid.add_argument("--duration", type=float, default=5,
                     help="Target duration in seconds (default: 5). Converted to num_frames "
                          "following the 8n+1 rule; max ~18s at 24fps")
    vid.add_argument("--image", default=None,
                     help="Input image URL or local path for image-to-video")
    vid.add_argument("--width", type=int, default=1152, help="Video width (default: 1152)")
    vid.add_argument("--height", type=int, default=768, help="Video height (default: 768)")
    vid.add_argument("--frame-rate", type=float, default=24, help="Frame rate 1-60 (default: 24)")
    vid.add_argument("--negative-prompt", default=None, help="Negative prompt")
    vid.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    vid.add_argument("--model", default=None, help="Override model (default: agnes-video-v2.0)")
    vid.add_argument("--output", required=True, help="Output file path")

    args = parser.parse_args()

    if args.command == "image":
        generate_image(args.prompt, args.size, args.ratio, args.output, args.image, args.model)
    elif args.command == "video":
        generate_video(args.prompt, args.duration, args.output, args.image,
                       args.width, args.height, args.frame_rate,
                       args.negative_prompt, args.seed, args.model)

    print("Done.")


if __name__ == "__main__":
    main()
