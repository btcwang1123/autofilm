# autofilm — MP4 / YouTube link → YouTube SRT 字幕工具

把 **本機 MP4 影片** 或 **YouTube 影片網址** 餵進去,自動產生上傳到 YouTube 用的 `.srt` 字幕檔。

流程:

```
本機 MP4 ──ffmpeg──▶ 音訊 WAV ──faster-whisper──▶ 逐段轉錄 ──錯別字規則修正──▶ .srt
YT 連結 ──yt-dlp──▶ 同左
```

## 安裝(第一次)

```powershell
# 1. Python 虛擬環境 + 依賴(會自動偵測 GPU,faster-whisper 會加速)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# 2. 確認 ffmpeg 可用(有裝就略過)
ffmpeg -version
#   若找不到:winget install --id Gyan.FFmpeg --scope user

# 3. 下載 Whisper 模型(只需一次,如 small 中文模型約 500MB)
python download_model.py
```

## 使用

**本機影片**:

```powershell
python srt_gen.py D:\videos\我的影片.mp4
```
輸出:`D:\videos\我的影片.srt`(與影片同名、同資料夾)。

**YouTube 影片網址**:

```powershell
python srt_gen.py "https://youtu.be/xxxxxxxxxxxx"
```
會自動下載音軌,輸出到「目前資料夾」下的 `<影片標題>.srt`。

**一次轉多支**(網址/本機檔可混合):

```powershell
python srt_gen.py https://youtu.be/aaa https://youtu.be/bbb D:\videos\c.mp4
```
依序處理、各自輸出 `.srt`(`<影片標題>.srt` 或本機檔同名)。全部結束才顯示總結。

**大量批次** — 把網址存在文字檔(每行一個,`#` 開頭會被當註解跳過):

```
# urls.txt
https://youtu.be/aaa
https://youtu.be/bbb
https://youtu.be/ccc
```
```powershell
python srt_gen.py urls.txt
```
這是最保險的方式:避開命令列網址含 `&` 等特殊字元被殼層誤解的問題。

**超簡單方式**:把 MP4 檔直接拖到 `run.bat` 上,或在視窗輸入 `run.bat 網址1 網址2 ...`(多個直接空格分開)或 `run.bat urls.txt`。

常用參數:

| 參數 | 說明 | 預設 |
|---|---|---|
| `--model` | 模型大小:`tiny` `base` `small` `medium` `large-v3` | `small` |
| `--lang` | 語言(留空自動偵測) | 空 = 自動 |
| `--out` | 指定輸出檔 | 自動依影片命名 |
| `--no-fix` | 關閉錯別字規則修正 | 開著 |

## 模型大小怎麼選

| 模型 | 速度(CPU) | 中文準確度 | 建議 |
|---|---|---|---|
| `tiny` | 極快 | 差 | 不建議 |
| `base` | 快 | 尚可 | 快速預覽 |
| `small` | 中等 | 良好 | **預設,日常用** |
| `medium` | 慢 | 很好 | 較長/較難影片 |
| `large-v3` | 很慢 | 最好 | 追求極致品質(需 GPU 佳) |

**指定模型大小**(預設 `small`,可隨時切換):

```powershell
python srt_gen.py https://youtu.be/xxx --model medium
python srt_gen.py urls.txt --model large-v3
```

也可透過 `run.bat` 帶參數:`run.bat urls.txt --model medium`。

首次使用某模型時會自動下載一次(medium 約 1.5GB、large 約 3GB,要網路)。之後離線可用。

> 註:`medium`/`large` 等大模型預設**關閉 VAD 靜音過濾**(大模型 VAD 較激進,有時把語音當靜音誤跳),由 Whisper 自行判段,確保不漏內容。`small` 以下維持 VAD 加速。

## 全程是怎麼跑出來的(細節說明)

1. **抽音軌**:ffmpeg 把 MP4 的音軌轉成 16kHz 單聲道 WAV(Whisper 最佳輸入)。
2. **轉錄**:faster-whisper(Whisper 的加速版)把語音切成片段逐段轉成文字,並記錄每段的開始/結束時間。
3. **錯別字訂正**:規則式修正(非 LLM,零成本、離線)。修正下列幾類:
   - **專有名詞/人名查表**:內建常見錯字對照表(如「劉備」「易建聯」等),可用 `corrections.json` 自訂(見下)。
   - **ADD 標記**:Whisper 常把英文/術語擋在括號外,套用**排除式邏輯**(不在白名單內的英文保留原樣)。對「ATK/ROC/RNG」這類遊戲術語不誤傷。
   - **全形/半形標點**:把「,」等地統一成正確中文標點、多餘空格移除。
4. **輸出 SRT**:組合成標準 SRT 時間軸,可直接上傳 YouTube。

### 自訂錯字對照(corrections.json)

在程式同目錄放一個 `corrections.json`(不存在也 OK,會自動建立範本):

```json
{
  "替換規則": { "錯字": "正確字" },
  "忽略名詞": []
}
```

- `"替換規則"`:逐字/逐詞把「誤植文字」換成「正確文字」(整句標準化,最常用)。例如 `{ "德特律": "底特律", "尼日利亚": "奈及利亞" }`。
- `"忽略名詞"`:要讓逐詞「首次修正」跳過的詞(例如人名、廠牌),避免被誤替換。

## 疑難排解

- **GPU 偵測**:`python -c "import faster_whisper"` 後跑一次看要不要裝 CUDA 工具。一般 CPU 就能用,只是較慢。
- **第一次下載模型很久**:模型第一次要下載,之後快取在本機。
- **YouTube 上傳字幕**:在 YouTube Studio → 字幕 → 上傳子標(Captions)→ 選「自動產生(如果沒有)」或直接選「.SRT」檔即可。

## License

個人使用工具。
