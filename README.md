# autofilm

Generate YouTube-ready `.srt` subtitle files from local MP4s or YouTube URLs — fully local and free.

```
Local MP4 ──ffmpeg──▶ audio ──faster-whisper──▶ segments ──typo fix──▶ .srt
YouTube URL ──yt-dlp──▶ same pipeline
```

Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (offline speech-to-text, runs on your machine — nothing uploaded), [yt-dlp](https://github.com/yt-dlp/yt-dlp) (download audio), and ffmpeg.

## Features

- ✅ Turn **local videos** (mp4/mkv/wav/...) or **YouTube URLs** into `.srt`
- ✅ **Batch mode**: multiple URLs / files in one run, or a `urls.txt` list file
- ✅ **Rule-based typo correction** (e.g. `TestFly` → `TestFlight`, simplified→traditional fixes), fully customizable
- ✅ **Model size choice**: `tiny` → `large-v3` for accuracy/speed tradeoff
- ✅ **No GPU required** — runs on CPU (GPU auto-detected if available)
- ✅ Works on **Windows / Linux / macOS**

## Quick Start (Windows)

The included **`run.bat` does everything for you** — create the venv, install dependencies, and process your files.

```bat
:: 1. Install ffmpeg once  (skip if already installed)
winget install Gyan.FFmpeg

:: 2. Clone
git clone https://github.com/btcwang1123/autofilm.git
cd autofilm

:: 3. Done. Just run it:
run.bat
```

`run.bat` auto-creates `.venv` and installs `requirements.txt` on first run. Then use one of these:

- **Type the command** (simplest to understand): `run.bat test.mp4` (run from the `autofilm` folder, so cmd finds `run.bat`; your MP4 can be anywhere, just use its path)
- Pass URLs / files directly: `run.bat "https://youtu.be/aaa" "https://youtu.be/bbb" video.mp4`
- Or a URL list: `run.bat urls.txt`
- Or **drag & drop**: open File Explorer, left-click your MP4 and, keeping the button held, drag it onto the `run.bat` icon and release. It runs `run.bat <your-file>` for you. Both ways do the same thing.

## Quick Start (Linux / macOS)

```bash
# 1. Install ffmpeg
sudo apt install ffmpeg      # Debian/Ubuntu   |   brew install ffmpeg   # macOS

# 2. Clone & set up
git clone https://github.com/btcwang1123/autofilm.git
cd autofilm
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## CLI Usage

```bash
# Single local video → video.srt next to it
python srt_gen.py path/to/video.mp4

# Single YouTube video → <video-title>.srt in current folder
python srt_gen.py "https://youtu.be/xxxxxxxxxxxx"

# Multiple inputs (mixed URLs and files)
python srt_gen.py "https://youtu.be/aaa" "https://youtu.be/bbb" path/to/c.mp4

# Batch from a list file (one URL per line, '#' = comment)
python srt_gen.py urls.txt
```

#### Example `urls.txt`

Create a plain text file named `urls.txt` in the autofilm folder, one URL per line.
Lines starting with `#` and empty lines are ignored, and you can mix YouTube links with local files:

```
# My weekly uploads — one item per line, '#' lines are skipped
https://youtu.be/aaa111
https://youtu.be/bbb222

# a local file also works (use the path syntax of your OS)
/home/me/videos/my-video.mp4      # Linux/macOS
D:\videos\my-video.mp4            # Windows

https://www.youtube.com/watch?v=ccc333
```

Then run `run.bat urls.txt` (Windows) or `python srt_gen.py urls.txt` (any OS) — each item becomes its own `.srt`.

### Options

| Arg | Description | Default |
|---|---|---|
| `--model` | Whisper model: `tiny` `base` `small` `medium` `large-v3` | `small` |
| `--lang` | Language code (e.g. `zh`, `en`); empty = auto-detect (applies to all inputs) | auto |
| `--device` | Device: `auto` / `cpu` / `cuda` | `auto` |
| `--no-fix` | Disable the typo-correction pass | on |

### Model size tradeoff

| Model | Speed (CPU) | Chinese accuracy | Tip |
|---|---|---|---|
| `tiny` | very fast | poor | not recommended |
| `base` | fast | ok | quick preview |
| `small` | medium | good | **default** |
| `medium` | slow | very good | longer/difficult videos |
| `large-v3` | very slow | best | max quality (GPU helps) |

```bash
python srt_gen.py "https://youtu.be/xxx" --model medium
python srt_gen.py urls.txt --model large-v3
```

The first time you use a model it is downloaded automatically (`medium` ≈1.5 GB, `large` ≈3 GB); afterward it is cached locally. You can pre-download with `python download_model.py`.

> **Note**: `medium`/`large` models disable the VAD silence filter by default — large-model VAD can be over-aggressive and skip real speech. The model's own segmentation handles it instead. `small` and below keep VAD for speed.

## How it works

1. **Audio extraction** — ffmpeg converts the video/audio track to a 16 kHz mono WAV (ideal for Whisper).
2. **Transcription** — faster-whisper splits speech into segments with timestamps.
3. **Typo correction (rule-based)** — offline & free:
   - **Term/lookup table**: bundled examples like `TestFly`→`TestFlight`, `德特律`→`底特律`, `尼日利亚`→`奈及利亞` — add your own in `corrections.json`.
   - **Foreign terms**: Whisper's `[ADD]` tags for uncertain English/tech terms (e.g. ATK/ROC/RNG) are kept as-is.
   - **Punctuation**: fullwidth commas/periods for Chinese subtitles, extra spaces removed.
4. **SRT output** — standard `.srt`, upload-ready.

## Customizing typo corrections

Create `corrections.json` in the project folder (auto-created with a template if missing):

```json
{
  "替换规则": { "wrong": "right" },
  "忽略名詞": []
}
```

- `替换规则` — string replacements applied to every segment (most common use).
- `忽略名詞` — terms to skip in per-token fixing (names, brands) so they aren't altered.

## Troubleshooting

- **ffmpeg not found**: verify `ffmpeg -version` works. If installed somewhere non-standard, set the `FFMPEG_PATH` env var to the ffmpeg executable. (On Windows, winget/standard installs are auto-detected.)
- **GPU**: runtime auto-detects; for GPU you must install NVIDIA CUDA tooling yourself. CPU works everywhere, just slower.
- **First model download is slow**: one-time download, cached afterward.
- **Uploading to YouTube**: YouTube Studio → Subtitles → Upload a file, choose your `.srt`.

## License

Personal-use tool.
