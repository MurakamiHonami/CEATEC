"""
実運用向けの判定スクリプト

texts.txt(1行1テキスト)を読み込み、アンサンブルモデルで判定して
results.csv に出力する。確信度が低い(境界線上の)判定には
人手レビュー推奨のフラグを立てる。

使い方:
    python predict.py texts.txt
    (texts.txt を省略した場合は入力を対話的に受け付ける)
"""

import csv
import sys
from datetime import datetime

from ensemble_inference import predict_ensemble
from blocklist_filter import check_blocklist

# この範囲の確信度は「判定が割れている境界事例」とみなし、人手レビュー推奨とする
REVIEW_THRESHOLD_LOW = 0.55
REVIEW_THRESHOLD_HIGH = 0.70


def classify_texts(texts: list[str]) -> list[dict]:
    results = []
    for text in texts:
        # ① 明確なNGワードは、機械的なブロックリストで即判定(BERTを待たない)
        blocklist_result = check_blocklist(text)
        if blocklist_result["matched"]:
            sources = ",".join(blocklist_result["matched_source"])
            results.append(
                {
                    "text": text,
                    "label": "ハラスメント・侮辱",
                    "confidence": 1.0,
                    "needs_review": False,
                    "source": f"blocklist({sources})",
                }
            )
            continue

        # ② ブロックリストに該当しない場合のみ、BERTアンサンブルで文脈判定
        r = predict_ensemble(text)
        needs_review = REVIEW_THRESHOLD_LOW <= r["confidence"] <= REVIEW_THRESHOLD_HIGH
        results.append(
            {
                "text": text,
                "label": r["label"],
                "confidence": round(r["confidence"], 4),
                "needs_review": needs_review,
                "source": "bert_ensemble",
            }
        )
    return results


def main():
    if len(sys.argv) > 1:
        # ファイルモード
        input_path = sys.argv[1]
        with open(input_path, encoding="utf-8") as f:
            texts = [line.strip() for line in f if line.strip()]
    else:
        # 対話モード
        print("テキストを1行ずつ入力してください(空行で終了):")
        texts = []
        while True:
            line = input("> ").strip()
            if not line:
                break
            texts.append(line)

    if not texts:
        print("判定するテキストがありません。")
        return

    results = classify_texts(texts)

    output_path = "predict.py_results.csv"

    is_save_csv_data = int(input("結果を保存しますか？0:しない、1:する"))

    if is_save_csv_data:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f, fieldnames=["text", "label", "confidence", "needs_review", "source"]
            )
            writer.writeheader()
            writer.writerows(results)
    

    review_count = sum(r["needs_review"] for r in results)
    harassment_count = sum(r["label"] == "ハラスメント・侮辱" for r in results)

    print(f"\n判定完了: {len(results)}件")
    print(f"  ハラスメント・侮辱と判定: {harassment_count}件")
    print(f"  人手レビュー推奨(境界事例): {review_count}件")
    print(f"結果を {output_path} に保存しました" if is_save_csv_data else "")


    for result in results:
        print("=" * 50)
        print(result["text"],result["label"],result["confidence"])


if __name__ == "__main__":
    main()
