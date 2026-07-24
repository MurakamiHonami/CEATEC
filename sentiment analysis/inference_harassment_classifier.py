"""
fine-tuning済みモデルで推論するスクリプト
train_harassment_classifier.py で保存したモデルを使う
"""

import torch
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "harassment_classifier", "final")

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
        "label": id2label[pred_id],
        "confidence": probabilities[pred_id].item(),
        "probabilities": {id2label[i]: probabilities[i].item() for i in id2label},
    }


if __name__ == "__main__":
    texts = [
        "頭悪いからできないよね",
        "ごめんね",
        "すみませんでした",
    ]
    for text in texts:
        print("*" * 50)
        result = predict(text)
        print(f"テキスト：{text}")
        print(f"判定：{result['label']}（確信度 {result['confidence']:.4f}）")
        print(f"内訳：{result['probabilities']}")
