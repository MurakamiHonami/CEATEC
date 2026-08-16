"""
複数シードで学習・評価を繰り返し、結果のブレ(平均・標準偏差)を確認するスクリプト

train_harassment_classifier.py を複数のシードで順番に実行し、
それぞれ eval_samples.csv で評価した結果を集計する。
「今のデータ量・設定で、平均するとどれくらいの性能が出るのか」
「シードによってどれくらいブレるのか」を確認する目的。

使い方:
    python run_multi_seed_experiment.py

注意:
    BERTの学習をシードの数だけ繰り返すため、時間がかかります
    （1シードあたり数分〜数十分、環境による）。
"""

import csv
import os
import subprocess
import sys

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_SCRIPT = os.path.join(BASE_DIR, "train_harassment_classifier.py")
EVAL_SAMPLES_PATH = os.path.join(BASE_DIR, "eval_samples.csv")
RESULTS_PATH = os.path.join(BASE_DIR, "multi_seed_results.csv")

SEEDS = [42, 123, 2024]


def evaluate(model_dir: str) -> dict:
    """指定したモデルをeval_samples.csvで評価してスコアを返す"""
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()

    import csv as _csv

    with open(EVAL_SAMPLES_PATH, encoding="utf-8-sig") as f:
        samples = list(_csv.DictReader(f))

    y_true, y_pred = [], []
    for row in samples:
        inputs = tokenizer(row["text"], truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        pred = torch.argmax(outputs.logits, dim=1).item()
        y_true.append(int(row["expected_label"]))
        y_pred.append(pred)

    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=1, zero_division=0
    )
    return {"accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}


def main():
    results = []

    for seed in SEEDS:
        output_dir = os.path.join(BASE_DIR, f"harassment_classifier_seed{seed}")
        print("=" * 60)
        print(f"シード {seed} で学習開始 -> {output_dir}")
        print("=" * 60)

        # train_harassment_classifier.py をサブプロセスとして実行
        # (プロセスを分けることで、シード間のtorch内部状態の
        #  持ち越しを防ぎ、より公平な比較にする)
        subprocess.run(
            [
                sys.executable,
                TRAIN_SCRIPT,
                "--seed", str(seed),
                "--output_dir", output_dir,
            ],
            check=True,
        )

        model_path = os.path.join(output_dir, "final")
        metrics = evaluate(model_path)
        metrics["seed"] = seed
        results.append(metrics)

        print(f"\nシード{seed}の結果: {metrics}\n")

    # ---- 集計 ----
    print("\n" + "=" * 60)
    print("全シードの結果")
    print("=" * 60)
    print(f"{'seed':>6} | {'accuracy':>8} | {'precision':>9} | {'recall':>7} | {'f1':>6}")
    for r in results:
        print(
            f"{r['seed']:>6} | {r['accuracy']:>8.4f} | {r['precision']:>9.4f} "
            f"| {r['recall']:>7.4f} | {r['f1']:>6.4f}"
        )

    print("\n" + "-" * 60)
    for metric in ["accuracy", "precision", "recall", "f1"]:
        values = [r[metric] for r in results]
        print(f"{metric:>10}: 平均={np.mean(values):.4f}  標準偏差={np.std(values):.4f}"
              f"  (最小={min(values):.4f} / 最大={max(values):.4f})")

    # ---- CSVに保存 ----
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["seed", "accuracy", "precision", "recall", "f1"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n結果を {RESULTS_PATH} に保存しました")


if __name__ == "__main__":
    main()
