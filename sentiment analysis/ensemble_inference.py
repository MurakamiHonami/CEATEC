"""
3シード分のモデルをアンサンブル(確率平均)して判定するスクリプト

run_multi_seed_experiment.py で作成した
harassment_classifier_seed42/final
harassment_classifier_seed123/final
harassment_classifier_seed2024/final
の3モデルを読み込み、それぞれの確率を平均して最終判定する。

単一モデルよりも、特定シードのクセに判定が引っ張られにくく、
安定した予測が期待できる。

使い方:
    from ensemble_inference import predict_ensemble
    result = predict_ensemble("頭悪いからできないよね")
"""

import os

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEDS = [42, 123, 2024]
MODEL_DIRS = [
    os.path.join(BASE_DIR, f"harassment_classifier_seed{seed}", "final") for seed in SEEDS
]

_models = []
_tokenizers = []


def _load_models():
    """初回呼び出し時にだけ全モデルをロードする(毎回ロードすると遅いため)"""
    if _models:
        return

    for model_dir, seed in zip(MODEL_DIRS, SEEDS):
        if not os.path.exists(model_dir):
            raise FileNotFoundError(
                f"モデルが見つかりません: {model_dir}\n"
                f"run_multi_seed_experiment.py を実行してseed{seed}分のモデルを"
                f"作成済みか確認してください。"
            )
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        model.eval()
        _tokenizers.append(tokenizer)
        _models.append(model)

    print(f"{len(_models)}個のモデルをロードしました: {SEEDS}")


def predict_ensemble(text: str, verbose: bool = False) -> dict:
    """
    3モデルの確率を平均して最終判定を返す。

    Returns:
        dict: {
            "label": 判定ラベル,
            "confidence": アンサンブル後の確信度,
            "probabilities": {ラベル名: 確率},
            "individual_predictions": シードごとの個別結果(verbose=True時のみ),
        }
    """
    _load_models()

    id2label = _models[0].config.id2label
    num_labels = len(id2label)

    all_probs = torch.zeros(num_labels)
    individual_predictions = []

    for seed, tokenizer, model in zip(SEEDS, _tokenizers, _models):
        inputs = tokenizer(text, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)[0]
        all_probs += probs

        if verbose:
            pred_id = torch.argmax(probs).item()
            individual_predictions.append(
                {
                    "seed": seed,
                    "label": id2label[pred_id],
                    "confidence": probs[pred_id].item(),
                }
            )

    avg_probs = all_probs / len(_models)
    pred_id = torch.argmax(avg_probs).item()

    result = {
        "label": id2label[pred_id],
        "confidence": avg_probs[pred_id].item(),
        "probabilities": {id2label[i]: avg_probs[i].item() for i in range(num_labels)},
    }
    if verbose:
        result["individual_predictions"] = individual_predictions

    return result


if __name__ == "__main__":
    texts = [
        "頭悪いからできないよね",
        "ごめんね",
        "すみませんでした",
        "まだ君ここにいたんだ",
        "能力ないんだから見てれば",
        "ずっと寝てればいいんじゃないですか？仕事できないんですし",
        "お仕事がとても丁寧で、いつまでも終わらないですね",
        "お仕事がとても丁寧で、いつまでも終わらないですね笑",
        "素晴らしい効率ですね",
        "ご立派な存在感でしたね、全員あなたのことをわらっていましたよ",
        "相変わらずお優しいことですね",
        "大人なのに、かわいらしい服装ですね",
        "随分と華やかな反省会でしたね",
        "お仕事がとても丁寧ですね",
        "いつまでも終わらないですね",
        "いつまでも",
        "終わらないですね",
        "本気なの", 
        "がんばるの",
        "やる気あるの",
        "やる気あるの？",
        "この料理",
        "おいしくない",
        "勉強できないです",
        "運動苦手です",
        "泳げないです",
        "この仕事できる？",
        "この仕事できる",
        "小さい猫好き",
        "君と仕事するのかぁ",
        "Fuck you",
        "ファックユー",
        "殺す",
        "Kill you",
        "kill you",
        "Nigger",
        "Nigga",
        "ニガー"
    ]
    
    for text in texts:
        print("*" * 50)
        result = predict_ensemble(text, verbose=True)
        print(f"テキスト：{text}")
        print(f"判定：{result['label']}（アンサンブル確信度 {result['confidence']:.4f}）")
        print(f"内訳：{result['probabilities']}")
        print("シードごとの個別結果:")
        for p in result["individual_predictions"]:
            print(f"  seed{p['seed']}: {p['label']} ({p['confidence']:.4f})")
