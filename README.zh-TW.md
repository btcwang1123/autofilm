# autofilm

> **繁體中文** · [English](README.md)

把**本機 MP4**或 **YouTube 網址**自動轉成可直接上傳到 YouTube 的 `.srt` 字幕檔——完全本機執行、免費,不會上傳任何內容到雲端。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

```
本機 MP4 ──ffmpeg──▶ 音訊 ──faster-whisper──▶ 分段轉錄 ──錯別字修正──▶ .srt
YouTube 網址 ──yt-dlp──▶ 同一個流程
```

技術核心:[faster-whisper](https://github.com/SYSTRAN/faster-whisper)(本機語音轉文字,影片不會被上傳)、[yt-dlp](https://github.com/yt-dlp/yt-dlp)(下載音軌)、ffmpeg(抽音軌)。

## 功能特色

- ✅ 把**本機影片**(mp4/mkv/wav/...)或 **YouTube 網址**轉成 `.srt`
- ✅ **批次處理**:一次多個網址/檔案,或用 `urls.txt` 清單檔(參考 `urls.example.txt`)
- ✅ **錯別字規則修正**(例:`TestFly` → `TestFlight`、簡轉繁),可自訂
- ✅ **可選模型大小**:`tiny` → `large-v3`,依需求在速度/準確度間取捨
- ✅ **即時進度條**:轉錄時清楚顯示跑到哪,不怕像卡住
- ✅ **不需要 GPU**——CPU 就能跑(有 GPU 會自動使用)
- ✅ 支援 **Windows / Linux / macOS**(需 Python 3.10+)

## Windows 快速開始

專案內附的 **`run.bat` 會幫你做好一切**——建立虛擬環境、安裝依賴、處理影片。

```bat
:: 1. 安裝 ffmpeg(裝過可跳過)
winget install Gyan.FFmpeg

:: 2. Clone 專案
git clone https://github.com/btcwang1123/autofilm.git
cd autofilm

:: 3. 完成,直接跑:
run.bat
```

`run.bat` 第一次執行會自動建立 `.venv` 並安裝 `requirements.txt`。接著用以下任一方式:

- **直接輸入指令**(最直覺):`run.bat test.mp4`(要在 `autofilm` 資料夾內執行,cmd 才找得到 run.bat;你的影片檔可以放任何地方,打完整路徑即可)
- **一次多個網址/檔案**:`run.bat "https://youtu.be/aaa" "https://youtu.be/bbb" video.mp4`
- **用網址清單檔**:`run.bat urls.txt`
- **拖曳 拖放**:開啟檔案總管,用滑鼠左鍵按住你的 MP4 檔,把它拖到 `run.bat` 的圖示上放開,就會自動執行 `run.bat 你的.mp4`。兩種方式結果一樣。

**執行畫面長這樣**(第一次會先做環境設定):

```
[2/3] Ensuring dependencies are installed (requirements.txt)...
Loading Whisper model: small ...

===== Processing [https://youtu.be/xxxxxxxxxxxx] =====
Downloading YouTube audio...
  Extracting audio...
Transcribing:  74%|█████████████▎ | 14.0/19s [00:00<00:00, 38.8s/s, 目前內容預覽]
  Done: 123 segments.
  ✓ Saved subtitles to: <影片標題>.srt
```

## Linux / macOS 快速開始

```bash
# 1. 安裝 ffmpeg
sudo apt install ffmpeg      # Debian/Ubuntu   |   brew install ffmpeg   # macOS

# 2. Clone 並建立環境
git clone https://github.com/btcwang1123/autofilm.git
cd autofilm
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 指令用法

```bash
# 單支本機影片 → 在同目錄產生 video.srt
python srt_gen.py 路徑/影片.mp4

# 單支 YouTube 影片 → 在目前資料夾產生 <影片標題>.srt
python srt_gen.py "https://youtu.be/xxxxxxxxxxxx"

# 多個輸入(網址與本機檔可混用)
python srt_gen.py "https://youtu.be/aaa" "https://youtu.be/bbb" 路徑/c.mp4

# 用清單檔批次處理(每行一個網址,'#' = 註解)
python srt_gen.py urls.txt
```

#### `urls.txt` 範例

Repo 內附可直接套用的範本 **`urls.example.txt`**。把它複製成 `urls.txt` 再填入你的連結:

```bat
copy urls.example.txt urls.txt    &   notepad urls.txt     :: Windows
cp urls.example.txt urls.txt      &&  nano urls.txt          # Linux / macOS
```

或自己建立,每行一個網址。以 `#` 開頭的行、空行都會被忽略;可以混入本機檔案路徑:

```
# 我的每週上傳 — 每行一個,'#' 開頭會被跳過
https://youtu.be/aaa111
https://youtu.be/bbb222

# 也可以放本機影片(依你的作業系統選路徑寫法)
/home/me/videos/my-video.mp4      # Linux/macOS
D:\videos\my-video.mp4            # Windows

https://www.youtube.com/watch?v=ccc333
```

然後執行 `run.bat urls.txt`(Windows)或 `python srt_gen.py urls.txt`(其他系統)——每個項目各會產生一個 `.srt`。

### 參數

| 參數 | 說明 | 預設 |
|---|---|---|
| `--model` | Whisper 模型:`tiny` `base` `small` `medium` `large-v3` | `small` |
| `--lang` | 語言代碼(如 `zh`、`en`);留空自動偵測(多個輸入時套用全部) | 自動 |
| `--device` | 運算裝置:`auto` / `cpu` / `cuda` | `auto` |
| `--no-fix` | 關閉錯別字修正 | 開啟 |

### 模型大小怎麼選

| 模型 | 速度(CPU) | 中文準確度 | 建議 |
|---|---|---|---|
| `tiny` | 極快 | 差 | 不建議 |
| `base` | 快 | 尚可 | 快速預覽 |
| `small` | 中等 | 良好 | **預設,日常用** |
| `medium` | 慢 | 很好 | 較長/較難影片 |
| `large-v3` | 很慢 | 最好 | 追求極致品質(建議有 GPU) |

```bash
python srt_gen.py "https://youtu.be/xxx" --model medium
python srt_gen.py urls.txt --model large-v3
```

首次使用某個模型會自動下載(`medium` 約 1.5 GB、`large` 約 3 GB);之後會快取在本機。也可以用 `python download_model.py` 預先下載。

> **注意**:`medium`/`large` 等大模型預設**關閉 VAD 靜音過濾**(大型模型的 VAD 有時過度激進,會把真正的語音誤當成靜音跳過),改由模型自行分段,確保不漏內容。`small` 以下維持 VAD 以加快速度。

## 流程說明

1. **抽音軌** — ffmpeg 把影片音軌轉成 16 kHz 單聲道 WAV(Whisper 最理想的輸入)。
2. **轉錄** — faster-whisper 把語音分段轉成文字,並記錄每段時間。
3. **錯別字訂正(規則式)** — 離線、免費:
   - **專有名詞/對照表**:內建如 `TestFly`→`TestFlight`、`德特律`→`底特律`、`尼日利亚`→`奈及利亞`,可在 `corrections.json` 增減。
   - **外文/術語**:Whisper 對不確定的英文/技術詞(如 ATK/ROC/RNG)會以 `[ADD]` 標記,保留原樣不誤傷。
   - **標點**:中文字幕統一全形標點、移除多餘空格。
4. **輸出 SRT** — 標準 `.srt`,可直接上傳。

## 自訂錯別字修正(corrections.json)

在專案資料夾放一個 `corrections.json`(不存在也會自動建立範本):

```json
{
  "替换规则": { "錯字": "正確字" },
  "忽略名詞": []
}
```

- `替换规则` — 對每段文字套用的字串替換(最常用)。
- `忽略名詞` — 逐詞修正時要跳過的詞(如人名、品牌),避免被誤改。

## 疑難排解

- **找不到 ffmpeg**:確認 `ffmpeg -version` 有輸出。若安裝在非標準位置,設 `FFMPEG_PATH` 環境變數指向 ffmpeg 執行檔。(Windows 上 winget/標準安裝位置會自動偵測。)
- **GPU**:執行時會自動偵測;想用 GPU 需自行安裝 NVIDIA CUDA 工具。CPU 到處都能跑,只是較慢。
- **第一次下載模型很久**:一次性下載,之後會快取在本機。
- **上傳到 YouTube**:YouTube Studio → 字幕 → 上傳字幕檔 → 選你的 `.srt`。

## 授權

[MIT](LICENSE)— 可自由使用、修改、散佈,也可商用,需保留原作者署名。
