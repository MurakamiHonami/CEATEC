"""
koheiduck_labeled.csv を仕分けするスクリプト

- sentiment が NEUTRAL 以外（NEGATIVE/POSITIVE） -> labeled_data.csv に追記
    NEGATIVE -> label 1（ハラスメント・侮辱の可能性あり、の代理ラベル）
    POSITIVE -> label 0（該当なし、の代理ラベル）
- sentiment が NEUTRAL -> to_review_manual.csv に保存（人手で目視判断）

注意:
NEGATIVE=ハラスメント と単純に決め打ちしているため、
「ただの謝罪・不満表明」等がNEGATIVEに混ざり誤ラベルになる
ケースがあります（例:「すみませんでした」がNEGATIVE判定された事例）。
labeled_data.csv に追記された分も、学習前に一度サンプルで
スポットチェックすることを推奨します。
"""

import csv
import os

INPUT_PATH = "koheiduck_labeled.csv"
LABELED_OUTPUT_PATH = "labeled_data.csv"
REVIEW_OUTPUT_PATH = "to_review_manual.csv"

SENTIMENT_TO_LABEL = {
    "NEGATIVE": 1,  # ハラスメント・侮辱の可能性ありの代理ラベル
    "POSITIVE": 0,  # 該当なしの代理ラベル
}


def load_existing_texts(path: str) -> set:
    """labeled_data.csv に既に存在するテキストの集合を取得（重複追記防止用）"""
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8-sig") as f:
        return {row["text"] for row in csv.DictReader(f)}


def main():
    with open(INPUT_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"入力件数: {len(rows)}")

    existing_texts = load_existing_texts(LABELED_OUTPUT_PATH)
    seen_in_this_run = set()

    auto_labeled_rows = []
    review_rows = []
    skipped_duplicates = 0

    for row in rows:
        text = row["text"]
        # labeled_data.csv に既にある、または今回の処理内で既出のテキストはスキップ
        if text in existing_texts or text in seen_in_this_run:
            skipped_duplicates += 1
            continue
        seen_in_this_run.add(text)
        sentiment = row["sentiment"]
        if sentiment == "NEUTRAL":
            review_rows.append(
                {
                    "text": row["text"],
                    "label": "",  # 人が目視でここに 0 or 1 を入力する
                    "confidence": row["confidence"],
                    "reason": f"koheiduck_{sentiment}",
                    "needs_review": True,
                }
            )
        else:
            auto_labeled_rows.append(
                {
                    "text": row["text"],
                    "label": SENTIMENT_TO_LABEL[sentiment],
                    "confidence": row["confidence"],
                    "reason": f"koheiduck_{sentiment}",
                    "needs_review": False,
                }
            )

    # labeled_data.csv が既に存在する場合は追記、なければ新規作成
    file_exists = os.path.exists(LABELED_OUTPUT_PATH)
    with open(LABELED_OUTPUT_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["text", "label", "confidence", "reason", "needs_review"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(auto_labeled_rows)

    with open(REVIEW_OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["text", "label", "confidence", "reason", "needs_review"]
        )
        writer.writeheader()
        writer.writerows(review_rows)

    print(f"重複のためスキップ: {skipped_duplicates} 件")
    print(f"labeled_data.csv に {len(auto_labeled_rows)} 件追記しました")
    print(f"  内訳: NEGATIVE(label=1) {sum(1 for r in auto_labeled_rows if r['label']==1)} 件 / "
          f"POSITIVE(label=0) {sum(1 for r in auto_labeled_rows if r['label']==0)} 件")
    print(f"to_review_manual.csv に {len(review_rows)} 件出力しました（label列に0か1を手入力してください）")
    print("\n※ NEGATIVE判定分は誤ラベルが混ざる可能性があるため、学習前に一部サンプルチェック推奨")


if __name__ == "__main__":
    main()
