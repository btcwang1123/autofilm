"""預先下載 Whisper 模型,以免第一次跑 srt_gen.py 時卡很久。"""
import argparse
import sys

from faster_whisper import download_model

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a Whisper model for later offline use")
    parser.add_argument("--model", default="small", help="Model size: tiny/base/small/medium/large-v3")
    parser.add_argument("--output-dir", default=None, help="Directory to store the model (defaults to faster-whisper cache)")
    args = parser.parse_args()

    path = download_model(args.model, output_dir=args.output_dir, local_files_only=False)
    print(f"模型已下載: {path}")


if __name__ == "__main__":
    sys.exit(main())
