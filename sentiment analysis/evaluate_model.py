"""
固定検証セット(eval_samples.csv)を使ったモデル評価スクリプト

学習データを追加するたびにこのスクリプトを実行して、
未知の文・多様なトピックに対する精度が本当に上がっているかを追跡する。

使い方:
    python evaluate_model.py

出力:
    - 全体のaccuracy / precision / recall / f1
    - 誤判定した文の一覧（label, 予測, 確信度付き）
    - 結果を eval_history.csv に追記（実行のたびに1行、精度の推移を記録）
"""

import csv
import os
from datetime import datetime

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

# スクリプト自身の場所を基準にパスを解決する
# （実行時のカレントディレクトリがどこであっても正しく動くようにするため）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "harassment_classifier", "final")
EVAL_SAMPLES_PATH = os.path.join(BASE_DIR, "eval_samples.csv")
HISTORY_PATH = os.path.join(BASE_DIR, "eval_history.csv")

print(f"モデルを探しているパス: {MODEL_PATH}")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"モデルが見つかりません: {MODEL_PATH}\n"
        f"train_harassment_classifier.py を実行してモデルを保存済みか確認してください。"
    )

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.eval()

id2label = model.config.id2label


def predict(text: str) -> dict:
    inputs = tokenizer(text, truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    probabilities = torch.softmax(outputs.logits, dim=1)[0]
    pred_id = torch.argmax(probabilities).item()
    return {
        "pred_label": pred_id,
        "confidence": probabilities[pred_id].item(),
    }


def main():
    with open(EVAL_SAMPLES_PATH, encoding="utf-8-sig") as f:
        samples = list(csv.DictReader(f))

    print(f"検証セット: {len(samples)}件\n")

    y_true = []
    y_pred = []
    mistakes = []

    for row in samples:
        text = row["text"]
        expected = int(row["expected_label"])
        result = predict(text)
        pred = result["pred_label"]

        y_true.append(expected)
        y_pred.append(pred)

        if pred != expected:
            mistakes.append(
                {
                    "text": text,
                    "expected": id2label[expected],
                    "predicted": id2label[pred],
                    "confidence": result["confidence"],
                }
            )

    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=1, zero_division=0
    )

    print("=" * 50)
    print("全体結果")
    print("=" * 50)
    print(f"accuracy : {accuracy:.4f}")
    print(f"precision: {precision:.4f}")
    print(f"recall   : {recall:.4f}")
    print(f"f1       : {f1:.4f}")

    print(f"\n誤判定 {len(mistakes)}/{len(samples)} 件:")
    for m in mistakes:
        print(
            f"  [{m['text']}] 正解={m['expected']} / 予測={m['predicted']} "
            f"(確信度 {m['confidence']:.4f})"
        )

    # ---- 履歴に追記（データを増やすたびの精度推移を追跡） ----
    file_exists = os.path.exists(HISTORY_PATH)
    with open(HISTORY_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["timestamp", "n_samples", "accuracy", "precision", "recall", "f1"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "n_samples": len(samples),
                "accuracy": round(accuracy, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            }
        )
    print(f"\n結果を {HISTORY_PATH} に記録しました（精度推移の追跡用）")


if __name__ == "__main__":
    main()
