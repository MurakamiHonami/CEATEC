"""
日本語ハラスメント・侮辱検出BERTモデルのfine-tuningスクリプト

前提:
- pip install transformers datasets scikit-learn torch --break-system-packages
- 学習データは labeled_data.csv として用意（列: text, label）
  label は 0 = 該当なし, 1 = ハラスメント・侮辱に該当 の2値を想定
  例:
    text,label
    "頭悪いからできないよね",1
    "ごめんね",0
    "すみませんでした",0
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_fscore_support, accuracy_score
from sklearn.utils.class_weight import compute_class_weight
import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding,
)
from datasets import Dataset

MODEL_NAME = "cl-tohoku/bert-base-japanese-v3"
DATA_PATH = "labeled_data.csv"
OUTPUT_DIR = "./harassment_classifier"
NUM_LABELS = 2  # 0: 該当なし, 1: ハラスメント・侮辱

ID2LABEL = {0: "該当なし", 1: "ハラスメント・侮辱"}
LABEL2ID = {v: k for k, v in ID2LABEL.items()}


def load_data(path: str):
    df = pd.read_csv(path)
    assert {"text", "label"}.issubset(df.columns), "labeled_data.csv には text, label 列が必要です"

    # ---- 診断: dropna前の状態を確認 ----
    print(f"読み込み直後の行数: {len(df)}")
    empty_text_count = (df["text"].isna() | (df["text"].astype(str).str.strip() == "")).sum()
    if empty_text_count > 0:
        print(f"警告: text列が空/NaNの行が {empty_text_count} 件あります")

    df = df.dropna(subset=["text", "label"])
    df["label"] = df["label"].astype(int)

    before = len(df)

    # ---- 診断: 実際に重複しているtextの中身を表示 ----
    dup_mask = df.duplicated(subset=["text"], keep=False)
    if dup_mask.sum() > 0:
        print(f"\n重複が検出されたテキスト（頻度上位10件を表示）:")
        dup_texts = df[dup_mask]["text"].value_counts().head(10)
        for text, count in dup_texts.items():
            print(f"  {count}回: {text!r}")
        print()

    # 完全一致の重複を除去（train/evalへのデータ漏洩を防ぐため）
    df = df.drop_duplicates(subset=["text"], keep="first")
    removed = before - len(df)
    if removed > 0:
        print(f"重複データを {removed} 件削除しました（{before} 件 -> {len(df)} 件）")

    return df


def main():
    # ---- 1. データ読み込み・分割 ----
    df = load_data(DATA_PATH)
    print(f"総データ数: {len(df)}")
    print(df["label"].value_counts())

    train_df, eval_df = train_test_split(
        df, test_size=0.15, random_state=42, stratify=df["label"]
    )

    train_ds = Dataset.from_pandas(train_df.reset_index(drop=True))
    eval_ds = Dataset.from_pandas(eval_df.reset_index(drop=True))

    # ---- 2. トークナイザ・モデル準備 ----
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, model_max_length=512)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=512)

    train_ds = train_ds.map(tokenize, batched=True)
    eval_ds = eval_ds.map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # ---- 3. クラス不均衡対策（ハラスメント該当は少数派になりがち） ----
    class_weights = compute_class_weight(
        class_weight="balanced",
        classes=np.array([0, 1]),
        y=train_df["label"].values,
    )
    class_weights_tensor = torch.tensor(class_weights, dtype=torch.float)
    print(f"クラス重み: {dict(zip(['該当なし', '該当あり'], class_weights))}")

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            logits = outputs.logits
            loss_fct = nn.CrossEntropyLoss(weight=class_weights_tensor.to(logits.device))
            loss = loss_fct(logits, labels)
            return (loss, outputs) if return_outputs else loss

    # ---- 4. 評価指標（accuracyだけでなくprecision/recall/F1も見る） ----
    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, preds, average="binary", pos_label=1, zero_division=0
        )
        acc = accuracy_score(labels, preds)
        return {
            "accuracy": acc,
            "precision": precision,  # 「該当あり」と判定したうち実際に正しかった割合
            "recall": recall,        # 実際の該当ケースをどれだけ拾えたか（見逃し検出はまずここを見る）
            "f1": f1,
        }

    # ---- 5. 学習設定 ----
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=2e-5,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=20,
        report_to="none",
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    # ---- 6. 学習実行 ----
    trainer.train()

    # ---- 7. 最終評価 ----
    metrics = trainer.evaluate()
    print("最終評価結果:", metrics)

    # ---- 8. モデル保存 ----
    trainer.save_model(f"{OUTPUT_DIR}/final")
    tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")
    print(f"モデルを {OUTPUT_DIR}/final に保存しました")


if __name__ == "__main__":
    main()
