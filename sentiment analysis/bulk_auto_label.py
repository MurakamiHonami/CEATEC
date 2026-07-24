"""
LLM(Claude)による一括自動ラベリングスクリプト

入力: raw_texts.txt（1行1テキスト、ラベルなしの生データ）
出力: labeled_data.csv（text, label, confidence, reason, needs_review）

使い方:
1. raw_texts.txt にラベル付けしたい文を1行ずつ入れる
2. このスクリプトを実行
3. labeled_data.csv の needs_review=True の行だけ人手でチェック・修正する
4. 確認が終わったら needs_review 列を削除して data.csv として
   train_harassment_classifier.py に渡す
"""

import anthropic
import json
import csv
import os
import time

client = anthropic.Anthropic()

LABELED_OUTPUT_PATH = "labeled_data.csv"
RAW_TEXTS_PATH = "raw_texts.txt"

SYSTEM_PROMPT = """あなたは日本語テキストのハラスメント・侮辱検出を行う専門家です。

明確な罵倒語がなくても、以下のようなニュアンスがあれば「侮辱・ハラスメントに該当する」と判定してください：
- 相手の能力・人格を暗に見下す表現（例：「頭悪いからできないよね」→ 該当。婉曲的に相手の知能を貶している）
- 皮肉・嫌味で相手を傷つける意図がある表現
- 威圧・支配しようとする表現

一方、以下のような表現は該当しません：
- 単なる謝罪（例：「ごめんね」「すみませんでした」）
- 事実の中立的な指摘のみで、見下しや悪意を伴わないもの

必ず以下のJSON形式のみで回答してください（説明文やコードブロック記号は不要）:
{"is_harassment": true/false, "confidence": 0.0〜1.0, "reason": "一文で判定理由"}
"""

# confidence がこの範囲なら人手チェック対象とする（境界事例）
REVIEW_THRESHOLD_LOW = 0.3
REVIEW_THRESHOLD_HIGH = 0.7


def label_text(text: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def load_existing_texts(path: str) -> set:
    """labeled_data.csv に既に存在するテキストの集合を取得（重複追記防止用）"""
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8-sig") as f:
        return {row["text"] for row in csv.DictReader(f)}


def main():
    with open(RAW_TEXTS_PATH, encoding="utf-8") as f:
        all_texts = [line.strip() for line in f if line.strip()]

    print(f"読み込んだテキスト: {len(all_texts)}件")

    existing_texts = load_existing_texts(LABELED_OUTPUT_PATH)

    # 既にlabeled_data.csvにある文と、raw_texts.txt内の重複行を除いてAPI呼び出し対象を絞る
    texts = []
    seen = set()
    skipped_duplicates = 0
    for t in all_texts:
        if t in existing_texts or t in seen:
            skipped_duplicates += 1
            continue
        seen.add(t)
        texts.append(t)

    print(f"重複のためスキップ: {skipped_duplicates}件")
    print(f"実際にラベリングするテキスト: {len(texts)}件")

    rows = []
    for i, text in enumerate(texts):
        try:
            result = label_text(text)
        except Exception as e:
            print(f"[{i}] エラー: {text[:20]}... -> {e}")
            continue

        confidence = result["confidence"]
        # true/false判定そのものが微妙な確信度の場合は要チェックフラグを立てる
        needs_review = REVIEW_THRESHOLD_LOW <= confidence <= REVIEW_THRESHOLD_HIGH

        rows.append(
            {
                "text": text,
                "label": int(result["is_harassment"]),
                "confidence": confidence,
                "reason": result["reason"],
                "needs_review": needs_review,
            }
        )

        if (i + 1) % 20 == 0:
            print(f"{i + 1}/{len(texts)} 件処理済み")

        time.sleep(0.1)  # レート制限対策（必要に応じて調整）

    # labeled_data.csv が既に存在する場合は追記、なければ新規作成
    file_exists = os.path.exists(LABELED_OUTPUT_PATH)
    with open(LABELED_OUTPUT_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["text", "label", "confidence", "reason", "needs_review"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    review_count = sum(r["needs_review"] for r in rows)
    print(f"完了。labeled_data.csv に {len(rows)} 件追記しました")
    print(f"うち人手チェック推奨: {review_count} 件（needs_review=True）")
    print("今回追記分のラベル内訳:")
    print(f"  該当あり: {sum(r['label'] for r in rows)} 件")
    print(f"  該当なし: {len(rows) - sum(r['label'] for r in rows)} 件")


if __name__ == "__main__":
    main()
