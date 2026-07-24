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
        print("Initializing toxicity detection model...")

        try:
            # 多言語毒性検出モデル（日本語対応）
            # textdetox/glot500-toxicity-classifier は2025年3月更新
            # 15言語対応の二値分類（有害/非有害）
            model_name = os.environ.get(
                'MODEL_NAME',
                'textdetox/glot500-toxicity-classifier'
            )

            # 毒性検出パイプラインの初期化
            classifier = pipeline(
                "text-classification",
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
    機械学習モデルを使用してテキストの毒性を分析

    Args:
        text: チェック対象のテキスト

    Returns:
        分析結果の辞書
    """
    if classifier is None:
        raise Exception("モデルが初期化されていません")

    try:
        # 毒性検出を実行
        result = classifier(text[:512])

        # 結果の解析
        # result = [[{'label': 'LABEL_0', 'score': 0.9}, {'label': 'LABEL_1', 'score': 0.1}]]
        # LABEL_0 = neutral (非有害), LABEL_1 = toxic (有害)
        if isinstance(result, list) and len(result) > 0:
            scores_list = result[0] if isinstance(result[0], list) else result
        else:
            scores_list = result

        # ラベルとスコアを辞書化
        label_scores = {item['label']: item['score'] for item in scores_list}

        # LABEL_0 = neutral (非有害), LABEL_1 = toxic (有害)
        neutral_score = label_scores.get('LABEL_0', 0.0)
        toxic_score = label_scores.get('LABEL_1', 0.0)

        # 判定ロジック: 毒性スコアが閾値以上なら不適切
        # 閾値を0.5に設定（50%以上の確信度で有害と判定された場合）
        threshold = 0.5
        is_inappropriate = toxic_score >= threshold

        # ラベルと理由の決定
        if is_inappropriate:
            top_label_ja = "不適切で攻撃的な発言"
            top_score = toxic_score
            reasons = [
                f"AIモデルが毒性のある発言と判定しました（毒性度: {toxic_score:.1%}）"
            ]
        else:
            top_label_ja = "適切な発言"
            top_score = neutral_score
            reasons = [
                f"問題は検出されませんでした（非有害: {neutral_score:.1%}, 有害: {toxic_score:.1%}）"
            ]

        return {
            'text': text,
            'is_inappropriate': is_inappropriate,
            'confidence': toxic_score if is_inappropriate else neutral_score,
            'top_label': top_label_ja,
            'top_score': top_score,
            'all_scores': {
                '非有害': neutral_score,
                '有害': toxic_score
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
    print("毒性検出モデルによるノンデリカシー発言検出テスト")
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
