"""MP4 / YouTube link → SRT 字幕產生器。

輸入可以是:
- 本機影片/Podcast 音檔:`python srt_gen.py D:\\videos\\film.mp4`
- YouTube link:`python srt_gen.py https://youtu.be/xxxx`(用 yt-dlp 下載音軌)

流程:
1. (URL 時)yt-dlp 下載音軌
2. ffmpeg 抽出音軌 → 16kHz mono WAV
3. faster-whisper 逐段轉錄(含時間戳)
4. 錯別字規則訂正
5. 輸出標準 .srt(可直接上傳 YouTube)

參數:
    python srt_gen.py <影片或YT連結> [--model medium] [--lang zh] [--out xxx.srt]
需要 GPU 會自動偵測;沒 GPU 就用 CPU(較慢)。

本機影片輸出:與影片同名同資料夾的 .srt
YT 影片輸出:目前資料夾下 <影片標題>.srt
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

# Windows 終端中文輸出安全
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from corrector import Corrector

# ffmpeg 搜尋順序:
#   1. FFMPEG_PATH 環境變數(非標準安裝時可自訂)
#   2. 系統 PATH 上的 ffmpeg
#   3. Windows winget 的標準安裝位置(自動掃描,不寫死使用者名稱)
def find_ffmpeg() -> str:
    import shutil

    candidates: list[str] = []
    if env := os.environ.get("FFMPEG_PATH"):
        candidates.append(env)
    candidates.append("ffmpeg")
    candidates.extend(_winget_ffmpeg_candidates())

    for cand in candidates:
        if shutil.which(cand) or Path(cand).exists():
            return cand
    raise RuntimeError(
        "找不到 ffmpeg。請先安裝並加到 PATH:winget install --id Gyan.FFmpeg "
        "(Linux/macOS:apt install ffmpeg / brew install ffmpeg),"
        "或設定 FFMPEG_PATH 環境變數指向 ffmpeg 執行檔。"
    )


def _winget_ffmpeg_candidates() -> list[str]:
    """掃描 winget 的標準安裝資料夾,找出 ffmpeg.exe(Gyan.FFmpeg)。"""
    import glob

    patterns = [
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    found: list[str] = []
    for pat in patterns:
        expanded = os.path.expandvars(pat)
        found.extend(glob.glob(expanded))
    return found


def is_url(s: str) -> bool:
    """判斷輸入是不是一個網址(YouTube link 等)。"""
    return bool(re.match(r"^(https?://|www\.)", s)) or "youtu" in s or "youtube" in s


def download_audio_from_url(url: str, out_dir: Path) -> tuple[Path, str]:
    """用 yt-dlp 下載 YouTube 音軌。回傳 (音檔路徑, 影片標題)。"""
    import yt_dlp

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out_dir / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        print("下載 YouTube 音軌…", file=sys.stderr)
        info = ydl.extract_info(url, download=True)
        title = (info.get("title") or "youtube_video").strip()

    # 下載完成後在 out_dir 找實際音檔(副檔名不定:m4a/webm/opus…)
    files = [p for p in out_dir.iterdir() if p.is_file() and not p.name.startswith(".")]
    if not files:
        raise RuntimeError("yt-dlp 下載完成但找不到音檔,請檢查連結是否有效。")
    return sorted(files, key=lambda p: p.stat().st_mtime)[-1], title


def sanitize_filename(name: str) -> str:
    """移除 Windows 檔案名稱不允許的字元。"""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip() or "video"


def extract_audio(ffmpeg: str, source: Path, wav: Path) -> None:
    """用 ffmpeg 把影片/音檔抽成 16kHz 單聲道 WAV(Whisper 最喜歡的格式)。"""
    subprocess.run(
        [
            ffmpeg, "-y", "-i", str(source),
            "-vn", "-ac", "1", "-ar", "16000",
            str(wav),
        ],
        check=True, capture_output=True,
    )


@dataclass
class Segment:
    start: float  # 秒
    end: float    # 秒
    text: str


def transcribe(model, wav: Path, language: str | None, vad: bool = True, show_progress: bool = True) -> list[Segment]:
    """用 faster-whisper 把 WAV 轉成含時間戳的片段。

    show_progress=True 時以 tqdm 顯示轉錄進度條(以音檔時間為單位),
    讓長影片執行時能確認沒卡住。
    """
    segments, info = model.transcribe(
        str(wav),
        language=language,      # None = 自動偵測
        vad_filter=vad,         # VAD 跳靜音:小模型加速,大模型另見下方
        beam_size=5,
    )
    if not show_progress:
        return [Segment(seg.start, seg.end, seg.text.strip()) for seg in segments]

    from tqdm import tqdm
    total = float(getattr(info, "duration", 0) or 0)
    pbar = tqdm(total=total, unit="s", desc="Transcribing",
                file=sys.stderr, ncols=78, disable=False)
    result: list[Segment] = []
    last_end = 0.0
    for seg in segments:
        result.append(Segment(seg.start, seg.end, seg.text.strip()))
        step = max(seg.end - last_end, 0.0)
        if step:
            pbar.update(step)
        last_end = seg.end
        pbar.set_postfix_str(seg.text.strip()[:18], refresh=False)
    pbar.close()
    return result


def segments_to_srt(segments: list[Segment], fixer: Corrector | None) -> str:
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        text = fixer.fix_segment(seg.text) if fixer else seg.text
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{_ts(seg.start)} --> {_ts(seg.end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def _ts(seconds: float) -> str:
    """秒數 → SRT 時間戳 00:00:00,000"""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_input_args(raw_inputs: list[str]) -> list[str]:
    """展開輸入:一般網址/檔案原樣保留;若是 .txt 清單檔,逐行讀出當作輸入。

    支援你把一堆網址存進 urls.txt(每行一個),一次轉全部,避開命令列引號問題。
    """
    expanded: list[str] = []
    for s in raw_inputs:
        if not is_url(s) and s.lower().endswith(".txt") and Path(s).exists():
            with open(s, encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
            print(f"從清單檔讀入 {len(lines)} 個輸入: {s}", file=sys.stderr)
            expanded.extend(lines)
        else:
            expanded.append(s)
    return expanded


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MP4 / YouTube link → SRT 字幕(可一次傳多個,也可傳 .txt 網址清單)"
    )
    parser.add_argument("inputs", nargs="+",
                        help="一個或多個影片檔路徑 / YouTube link / .txt 網址清單檔")
    parser.add_argument("--model", default="small",
                        help="Whisper 模型:tiny/base/small/medium/large-v3(預設 small)")
    parser.add_argument("--lang", default=None,
                        help="語言代碼(zh/zh-TW/en...),留空自動偵測;多個輸入時套用到全部")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto",
                        help="運算裝置,預設自動偵測 GPU")
    parser.add_argument("--no-fix", action="store_true", help="關閉錯別字訂正")
    args = parser.parse_args()

    inputs = parse_input_args(args.inputs)
    if not inputs:
        print("錯誤:輸入清單為空", file=sys.stderr)
        return 1

    corrections_path = Path(__file__).parent / "corrections.json"
    fixer = Corrector.load(corrections_path) if not args.no_fix else None

    # 檢查本機檔案是否都存在(避免首個有效、後續失效時中途才爆)
    missing = [s for s in inputs if not is_url(s) and not Path(s).exists()]
    if missing:
        for m in missing:
            print(f"錯誤:找不到檔案 {m}", file=sys.stderr)
        return 1

    # 載入 Whisper 模型(一次,之後所有影片共用)
    print(f"載入 Whisper 模型:{args.model} …", file=sys.stderr)
    from faster_whisper import WhisperModel
    model = WhisperModel(
        args.model,
        device="auto" if args.device == "auto" else args.device,
        compute_type="auto",  # GPU 會自動用 fp16,CPU 用 int8
    )

    failed = 0
    with tempfile.TemporaryDirectory(prefix="autofilm_") as tmp_str:
        tmp = Path(tmp_str)

        for idx, src in enumerate(inputs, start=1):
            print(f"\n===== 處理 [{src}] =====", file=sys.stderr)
            try:
                if is_url(src):
                    # YouTube link:先下載音軌,輸出檔名用影片標題
                    audio, title = download_audio_from_url(src, tmp)
                    source_name = sanitize_filename(title)
                    print(f"  下載完成:{source_name}", file=sys.stderr)
                    out = Path.cwd() / f"{source_name}.srt"
                else:
                    audio = Path(src)
                    out = audio.with_suffix(".srt")

                wav = tmp / f"audio_{idx}.wav"  # 每輪獨立檔名,順序處理
                t0 = time.time()
                print("抽音軌…", file=sys.stderr)
                extract_audio(find_ffmpeg(), audio, wav)
                print(f"  完成({time.time()-t0:.1f}s),開始轉錄…", file=sys.stderr)
                t0 = time.time()
                # 大型模型 VAD 對某些音軌過度激進(把語音當靜音跳過),
                # 故 medium/large 以上的模型預設關閉 VAD,由 Whisper 自行判段。
                use_vad = not any(k in args.model.lower() for k in ("medium", "large"))
                segments = transcribe(model, wav, args.lang, vad=use_vad)
                print(f"  轉錄完成,共 {len(segments)} 段({time.time()-t0:.1f}s)", file=sys.stderr)

                srt = segments_to_srt(segments, fixer)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(srt, encoding="utf-8")
                print(f"  ✓ 字幕已輸出: {out} ({len(segments)} 段)")
            except Exception as e:
                failed += 1
                print(f"  ✗ 處理失敗 [{src}]: {e}", file=sys.stderr)

    print(f"\n完成:成功 {len(inputs) - failed} 個,失敗 {failed} 個", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
