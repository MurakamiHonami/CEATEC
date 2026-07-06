import json
import os
from typing import Dict, Any, List

# transformersは初回インポート時にモデルをロード
from transformers import pipeline
import torch

# グローバル変数でモデルをキャッシュ（Lambda環境での再利用のため）
classifier = None


def initialize_model():
    """モデルの初期化"""
    global classifier

    if classifier is None:
        print("Initializing text classification model...")

        try:
            # 日本語感情分析・毒性検出用のモデル
            # cohereの多言語embed+ゼロショットではなく、より直接的なアプローチ
            model_name = os.environ.get(
                'MODEL_NAME',
                'cardiffnlp/xlm-roberta-base-sentiment-multilingual'  # 多言語感情分析
            )

            # 感情分析パイプラインの初期化
            classifier = pipeline(
                "sentiment-analysis",
                model=model_name,
                device=-1,  # CPUを使用
                top_k=None  # 全ラベルのスコアを取得
            )
            print("Model initialized successfully")
        except Exception as e:
            print(f"Error initializing model: {e}")
            raise Exception("モデルの初期化に失敗しました。Lambda環境を確認してください。")


def analyze_text_with_ml(text: str) -> Dict[str, Any]:
    """
    機械学習モデルを使用してテキストを分析

    Args:
        text: チェック対象のテキスト

    Returns:
        分析結果の辞書
    """
    if classifier is None:
        raise Exception("モデルが初期化されていません")

    try:
        # 感情分析を実行
        result = classifier(text[:512])

        # 結果の解析
        # result = [[{'label': 'positive', 'score': 0.9}, {'label': 'negative', 'score': 0.1}, ...]]
        if isinstance(result, list) and len(result) > 0:
            scores_list = result[0] if isinstance(result[0], list) else result
        else:
            scores_list = result

        # ラベルとスコアを辞書化
        label_scores = {item['label']: item['score'] for item in scores_list}

        # 多言語感情分析モデルのラベル: Positive, Neutral, Negative
        positive_score = label_scores.get('positive', label_scores.get('Positive', label_scores.get('POSITIVE', 0.0)))
        neutral_score = label_scores.get('neutral', label_scores.get('Neutral', label_scores.get('NEUTRAL', 0.0)))
        negative_score = label_scores.get('negative', label_scores.get('Negative', label_scores.get('NEGATIVE', 0.0)))

        # ラベルマッピング（大文字小文字を考慮）
        for key in label_scores.keys():
            if key.lower() == 'positive':
                positive_score = label_scores[key]
            elif key.lower() == 'neutral':
                neutral_score = label_scores[key]
            elif key.lower() == 'negative':
                negative_score = label_scores[key]

        # 判定ロジック:
        # Negativeスコアが高い = 不適切な可能性
        # ただし、Negativeは「悲しい」「失望」なども含むので、閾値を高めに設定
        # かつ、Positiveが極端に低いことも考慮
        is_inappropriate = (
            negative_score > 0.7 or  # 強いネガティブ
            (negative_score > 0.5 and positive_score < 0.1)  # 中程度のネガティブ + ポジティブがほぼ0
        )

        # ラベルと信頼度の決定
        if negative_score > positive_score and negative_score > neutral_score:
            top_label_ja = "ネガティブな発言"
            top_score = negative_score
            if is_inappropriate:
                top_label_ja = "不適切で攻撃的な発言"
        elif positive_score > negative_score and positive_score > neutral_score:
            top_label_ja = "ポジティブな発言"
            top_score = positive_score
        else:
            top_label_ja = "中立的な発言"
            top_score = neutral_score

        # 理由の生成
        if is_inappropriate:
            reasons = [
                f"AIモデルが「{top_label_ja}」と判定しました（ネガティブ度: {negative_score:.1%}）"
            ]
        else:
            reasons = [
                f"問題は検出されませんでした（ポジティブ: {positive_score:.1%}, 中立: {neutral_score:.1%}, ネガティブ: {negative_score:.1%}）"
            ]

        return {
            'text': text,
            'is_inappropriate': is_inappropriate,
            'confidence': negative_score if is_inappropriate else max(positive_score, neutral_score),
            'top_label': top_label_ja,
            'top_score': top_score,
            'all_scores': {
                'ポジティブ': positive_score,
                '中立': neutral_score,
                'ネガティブ': negative_score
            },
            'reasons': reasons
        }

    except Exception as e:
        print(f"Error in ML inference: {e}")
        import traceback
        traceback.print_exc()
        raise


def lambda_handler(event, context):
    """
    AWS Lambda handler関数

    Args:
        event: Lambda イベント
            期待される形式:
            {
                "text": "チェック対象のテキスト"
            }
            または
            {
                "texts": ["テキスト1", "テキスト2", ...]
            }
        context: Lambda コンテキスト

    Returns:
        レスポンス
    """
    try:
        # モデルの初期化（初回のみ）
        initialize_model()

        # イベントボディの取得
        if isinstance(event, str):
            body = json.loads(event)
        elif 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        # 単一テキストまたは複数テキストの処理
        if 'text' in body:
            # 単一テキストの処理
            text = body['text']

            if not text or not text.strip():
                result = {
                    'text': text,
                    'is_inappropriate': False,
                    'confidence': 0.0,
                    'reasons': ['空のテキストです'],
                    'top_label': 'N/A',
                    'top_score': 0.0,
                    'all_scores': {}
                }
            else:
                result = analyze_text_with_ml(text)

            response_body = {
                'success': True,
                'result': result
            }
        elif 'texts' in body:
            # 複数テキストの処理
            texts = body['texts']
            results = []

            for text in texts:
                if not text or not text.strip():
                    results.append({
                        'text': text,
                        'is_inappropriate': False,
                        'confidence': 0.0,
                        'reasons': ['空のテキストです'],
                        'top_label': 'N/A',
                        'top_score': 0.0,
                        'all_scores': {}
                    })
                else:
                    results.append(analyze_text_with_ml(text))

            response_body = {
                'success': True,
                'results': results
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Invalid request format. Expected "text" or "texts" field.'
                }, ensure_ascii=False)
            }

        return {
            'statusCode': 200,
            'body': json.dumps(response_body, ensure_ascii=False),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            }, ensure_ascii=False)
        }


# ローカルテスト用
if __name__ == '__main__':
    # テストケース
    test_cases = [
        "こんにちは、良い天気ですね",
        "お前はバカだから何もできない",
        "この商品は素晴らしいです",
        "マジでうざいから消えろよ",
        "ご協力ありがとうございます",
        "馬鹿げた話ですね",  # 慣用表現
        "デブ猫ちゃんかわいい",  # 文脈次第
        "この人は本当に役立たず",  # キーワードなしだが侮辱的
    ]

    print("=" * 80)
    print("機械学習ベースのノンデリカシー発言検出テスト")
    print("=" * 80)
    print()

    for test_text in test_cases:
        event = {'text': test_text}
        result = lambda_handler(event, None)
        result_body = json.loads(result['body'])

        if result_body['success']:
            r = result_body['result']
            status = "⚠️ 不適切" if r['is_inappropriate'] else "✅ 適切"
            print(f"{status} | {test_text}")
            print(f"  判定: {r['top_label']} (信頼度: {r['top_score']:.1%})")
            print(f"  理由: {r['reasons'][0]}")
            print()
