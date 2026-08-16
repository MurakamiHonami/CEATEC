"""
学習データ(labeled_data.csv)から、句読点を除去したバージョンを生成して
追加するスクリプト。

WebSpeech等の音声認識結果には句読点が一切付かないため、
書き言葉(句読点あり)で作った学習データだけでは、実際の音声認識
テキストに対して系統的なズレが生じる。
このスクリプトは、既存の全データについて句読点(、。！？)を除去した
コピーを作り、学習データに追加することで、句読点の有無に関わらず
同じ判断ができるようにする(データ拡張)。

使い方:
    python augment_remove_punctuation.py
"""

import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, "labeled_data.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "additional_labeled_data_punctuation_free.csv")

# 音声認識結果には基本的に付かない記号
PUNCTUATION_CHARS = "、。！？,.!?"


def strip_punctuation(text: str) -> str:
    for ch in PUNCTUATION_CHARS:
        text = text.replace(ch, "")
    return text.strip()


def main():
    with open(INPUT_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"元データ: {len(rows)}件")

    existing_texts = {row["text"] for row in rows}

    new_rows = []
    skipped = 0
    for row in rows:
        stripped = strip_punctuation(row["text"])

        # 元々句読点がなかった文(変化なし)や、既に存在する文はスキップ
        # (重複を防ぐため)
        if stripped == row["text"] or stripped in existing_texts:
            skipped += 1
            continue

        new_rows.append(
            {
                "text": stripped,
                "label": row["label"],
                "confidence": 1.0,
                "reason": "punctuation_stripped_augmentation",
                "needs_review": False,
            }
        )
        existing_texts.add(stripped)  # 今回の処理内での重複も防ぐ

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["text", "label", "confidence", "reason", "needs_review"]
        )
        writer.writeheader()
        writer.writerows(new_rows)

    print(f"句読点除去バージョンを {len(new_rows)}件 生成しました")
    print(f"(変化なし/重複のためスキップ: {skipped}件)")
    print(f"出力先: {OUTPUT_PATH}")
    print("\n中身を確認したうえで、labeled_data.csv に追記してください:")
    print(
        "  Get-Content .\\additional_labeled_data_punctuation_free.csv "
        "| Select-Object -Skip 1 | Add-Content .\\labeled_data.csv"
    )


if __name__ == "__main__":
    main()
