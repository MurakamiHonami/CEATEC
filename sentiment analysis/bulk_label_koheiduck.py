"""
koheiduck/bert-japanese-finetuned-sentiment を使った一括判定スクリプト

注意:
このモデルは「ハラスメント/侮辱」を直接判定するモデルではなく、
positive / negative / neutral の3値感情極性分類モデルです。
ここでは NEGATIVE 判定を「ハラスメント・侮辱の可能性がある文」の
簡易的な代理指標(proxy)として扱いますが、罵倒語を含まない
見下し表現などは NEUTRAL に分類され、見逃す可能性が高い点に
注意してください（LLM判定スクリプトとの比較用と考えてください）。

入力: raw_texts.txt（1行1テキスト）
出力: koheiduck_labeled.csv
"""

import csv
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_NAME = "koheiduck/bert-japanese-finetuned-sentiment"

model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, model_max_length=512)
model.eval()

id2label = model.config.id2label  # {0: 'NEUTRAL', 1: 'NEGATIVE', 2: 'POSITIVE'}


def classify(text: str) -> dict:
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    probabilities = torch.softmax(outputs.logits, dim=1)[0]
    pred_id = torch.argmax(probabilities).item()
    sentiment_label = id2label[pred_id]

    return {
        "sentiment": sentiment_label,
        "confidence": probabilities[pred_id].item(),
        # NEGATIVE判定を簡易的な「ハラスメントの可能性あり」の代理フラグとして出力
        # (罵倒語を伴わない見下し表現は拾えない点に注意)
        "harassment_proxy_flag": sentiment_label == "NEGATIVE",
        "probabilities": {id2label[i]: probabilities[i].item() for i in id2label},
    }


def main():
    with open("raw_texts.txt", encoding="utf-8") as f:
        texts = [line.strip() for line in f if line.strip()]

    print(f"{len(texts)}件のテキストを判定します")

    rows = []
    for text in texts:
        result = classify(text)
        rows.append(
            {
                "text": text,
                "sentiment": result["sentiment"],
                "confidence": round(result["confidence"], 4),
                "harassment_proxy_flag": result["harassment_proxy_flag"],
                "prob_NEUTRAL": round(result["probabilities"].get("NEUTRAL", 0), 4),
                "prob_NEGATIVE": round(result["probabilities"].get("NEGATIVE", 0), 4),
                "prob_POSITIVE": round(result["probabilities"].get("POSITIVE", 0), 4),
            }
        )

    with open("koheiduck_labeled.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "text",
                "sentiment",
                "confidence",
                "harassment_proxy_flag",
                "prob_NEUTRAL",
                "prob_NEGATIVE",
                "prob_POSITIVE",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("完了。koheiduck_labeled.csv に出力しました")
    print("sentiment内訳:")
    for label in id2label.values():
        count = sum(1 for r in rows if r["sentiment"] == label)
        print(f"  {label}: {count} 件")


if __name__ == "__main__":
    main()
