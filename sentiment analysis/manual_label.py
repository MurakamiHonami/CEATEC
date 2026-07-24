"""
手動ラベリングツール（モデル・APIキー一切不要）

raw_texts.txt の各テキストを1件ずつ表示し、
自分で 0（該当なし）/ 1（ハラスメント・侮辱）を入力してラベル付けする。

使い方:
1. raw_texts.txt にラベル付けしたい文を1行ずつ入れる
2. このスクリプトを実行
3. 表示された文に対して 0 か 1 を入力してEnter
   - 0 : 該当なし
   - 1 : ハラスメント・侮辱に該当
   - s : この文をスキップ（labeled_data.csvには保存しない）
   - q : ここまでの入力を保存して終了

途中で終了しても、それまでの入力は都度 labeled_data.csv に
保存されているので、次回実行時は続きから再開できます
（既にラベル付け済みの文は自動的にスキップされます）。
"""

import csv
import os

RAW_TEXTS_PATH = "raw_texts.txt"
LABELED_OUTPUT_PATH = "labeled_data.csv"

FIELDNAMES = ["text", "label", "confidence", "reason", "needs_review"]


def load_existing_texts(path: str) -> set:
    """labeled_data.csv に既に存在するテキストの集合を取得（重複・再ラベリング防止用）"""
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8-sig") as f:
        return {row["text"] for row in csv.DictReader(f)}


def append_row(path: str, row: dict):
    """1件ずつ即保存する（途中終了しても進捗が消えないように）"""
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    with open(RAW_TEXTS_PATH, encoding="utf-8") as f:
        all_texts = [line.strip() for line in f if line.strip()]

    existing_texts = load_existing_texts(LABELED_OUTPUT_PATH)
    remaining = [t for t in all_texts if t not in existing_texts]

    print(f"全体: {len(all_texts)}件 / ラベル付け済み: {len(existing_texts)}件 / 残り: {len(remaining)}件")
    print("入力方法: 0=該当なし / 1=ハラスメント・侮辱 / s=スキップ / q=保存して終了\n")

    if not remaining:
        print("ラベル付けが必要なテキストはありません。")
        return

    labeled_count = 0
    for i, text in enumerate(remaining, start=1):
        print("*" * 50)
        print(f"[{i}/{len(remaining)}] {text}")

        while True:
            choice = input("ラベル (0/1/s/q): ").strip().lower()
            if choice in ("0", "1"):
                append_row(
                    LABELED_OUTPUT_PATH,
                    {
                        "text": text,
                        "label": int(choice),
                        "confidence": 1.0,  # 手動ラベル = 正解データとみなし満点扱い
                        "reason": "manual",
                        "needs_review": False,
                    },
                )
                labeled_count += 1
                break
            elif choice == "s":
                print("スキップしました（保存されません）")
                break
            elif choice == "q":
                print(f"\n終了します。今回 {labeled_count} 件ラベル付けしました。")
                return
            else:
                print("0, 1, s, q のいずれかを入力してください")

    print(f"\n全件終了。今回 {labeled_count} 件ラベル付けしました。")


if __name__ == "__main__":
    main()
