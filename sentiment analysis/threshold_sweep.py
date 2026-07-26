"""
判定閾値(threshold)を変えながらprecision/recall/f1を比較するスクリプト
再学習は不要。今のモデルの「ハラスメント確率がいくつ以上なら1と判定するか」
のラインだけを変えて、最も良いバランスの閾値を探す。

背景:
誤判定が「正解=該当なし→予測=ハラスメント」(過検知)ばかりで、
見逃しがほぼ無いという結果が出ている場合、判定の基準を厳しくする
(閾値を上げる)ことで、見逃しをあまり増やさずに過検知を減らせる
可能性がある。

使い方:
    python threshold_sweep.py
"""

import csv
import os

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "harassment_classifier", "final")
EVAL_SAMPLES_PATH = os.path.join(BASE_DIR, "eval_samples.csv")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"モデルが見つかりません: {MODEL_PATH}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.eval()

id2label = model.config.id2label
# ラベル名から「ハラスメント・侮辱」に対応するインデックスを取得
label2id = {v: k for k, v in id2label.items()}
POSITIVE_ID = label2id["ハラスメント・侮辱"]


def get_positive_probability(text: str) -> float:
    """「ハラスメント・侮辱」ラベルの確率だけを返す"""
    inputs = tokenizer(text, truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    probabilities = torch.softmax(outputs.logits, dim=1)[0]
    return probabilities[POSITIVE_ID].item()


def main():
    with open(EVAL_SAMPLES_PATH, encoding="utf-8-sig") as f:
        samples = list(csv.DictReader(f))

    # 1回だけ全件の確率を計算し、閾値ごとに使い回す（同じ推論を何度もしない）
    texts = [row["text"] for row in samples]
    y_true = [int(row["expected_label"]) for row in samples]
    y_prob = [get_positive_probability(t) for t in texts]

    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

    print(f"{'閾値':>6} | {'accuracy':>8} | {'precision':>9} | {'recall':>7} | {'f1':>6}")
    print("-" * 50)

    results = []
    for th in thresholds:
        y_pred = [1 if p >= th else 0 for p in y_prob]
        acc = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="binary", pos_label=1, zero_division=0
        )
        results.append((th, acc, precision, recall, f1))
        print(f"{th:>6.1f} | {acc:>8.4f} | {precision:>9.4f} | {recall:>7.4f} | {f1:>6.4f}")

    best = max(results, key=lambda r: r[4])  # f1が最も高い閾値
    print(f"\nf1が最も高い閾値: {best[0]} (f1={best[4]:.4f})")
    print("\n※ 閾値を上げすぎると見逃し(recall低下)が増えるので、")
    print("   運用上どちらを重視するか(誤検知を減らす vs 見逃しを減らす)で選んでください。")


if __name__ == "__main__":
    main()
