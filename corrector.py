"""錯別字規則訂正(非 LLM,離線、零成本)。

處理兩類問題:
1. 專有名詞/人名錯字 —— 對照表置換(`corrections.json` 可自訂)。
2. 打字表現標準化 —— 全形標點、去除多餘空白。

對 Whisper 用 [ADD] 標記的「不確定片段」,採取排除式處理:
- 純中文 → 套用對照表
- 含英文/數字/術語(ATK、ROC、RNG…)→ 原樣保留,避免誤傷
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_CORRECTIONS: dict[str, str] = {
    # 人名 / 專有名詞(把 Whisper 常見誤植改成正確用字)
    "德特律": "底特律",
    "尼日利亚": "奈及利亞",
    # 英文術語可放在「忽略名詞」而非取代規則,以避免誤傷
}


@dataclass
class Corrector:
    rules: dict[str, str] = field(default_factory=dict)
    ignore: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, path: str | Path) -> "Corrector":
        p = Path(path)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"替换规则": DEFAULT_CORRECTIONS, "忽略名詞": []}, f, ensure_ascii=False, indent=2)

        with open(p, encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            rules={k: v for k, v in data.get("替换规则", {}).items()},
            ignore=set(data.get("忽略名詞", [])),
        )

    def fix_segment(self, text: str) -> str:
        """訂正單一字幕行,回傳修正後文字(修正前不可復原則整行保留 ADD 語法)。"""
        add_verbs = re.findall(r"\[([^\[\]]+)\]", text)

        # 1) ADD 片段:純中文套用對照表,其餘(英文/數字)保留
        for part in add_verbs:
            if part in self.ignore:
                continue
            if re.fullmatch(r"[一-鿿]{1,6}", part):
                text = text.replace(f"[{part}]", self.rules.get(part, part))
            # 非純中文(含英文/數字)→ 原樣保留

        # 2) 移除殘留的 ADD 括號標記
        text = re.sub(r"[\[\]]", "", text)

        # 3) 替換規則(整段掃描)
        for src, dst in self.rules.items():
            if src != dst:
                text = text.replace(src, dst)

        # 4) 標點與空白標準化
        return _normalize_punct(text).strip()


def _normalize_punct(text: str) -> str:
    """統一標點、壓掉多餘空白。

    含中文的句子:標點轉為全形(符合 YouTube 中文字幕習慣)。
    純英文/數字:保留半形標點,不亂轉。"""
    text = unicodedata.normalize("NFKC", text)
    has_chinese = re.search(r"[一-鿿]", text) is not None
    if has_chinese:
        for half, full in ((",", "，"), (".", "。"), ("!", "！"), ("?", "？"), (";", "；"), (":", "：")):
            text = text.replace(half, full)
        # 全形標點後的多餘半形空格移除(中文排版不留空格)
        text = re.sub(r"([，。！？；：]) +", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    c = Corrector.load("corrections.json")
    sample = "今天的[ATK]很高,來自[尼日利亚]的[MOD]要買嗎?"
    print("sample:", sample)
    print("fixed :", c.fix_segment(sample))
