"""
NGワード検出のブロックリストフィルタ(2系統)

① ng_words.txt: 日本語など、独自に用意したNGワードリスト
② better-profanity: 英語圏のFワード・Nワード等、既製の禁止語ライブラリ
   (pip install better-profanity が必要。中身の単語リストはライブラリ側が
    保持しているものをそのまま使うので、こちらでは一切列挙していない)

文脈判断が不要な、明確に禁止すべき単語は、BERTモデルより先に
このフィルタで検出する。BERTモデルは「文脈依存の皮肉・嫌味」のような、
ブロックリストでは判定できない難しいケースに専念させる設計。

使い方:
    from blocklist_filter import check_blocklist
    result = check_blocklist("テキスト")
    if result["matched"]:
        print("NGワード検出:", result["matched_words"])
"""

import os
import unicodedata

try:
    from better_profanity import profanity as _english_profanity
    _english_profanity.load_censor_words()
    _ENGLISH_FILTER_AVAILABLE = True
except ImportError:
    _ENGLISH_FILTER_AVAILABLE = False
    print(
        "警告: better-profanity がインストールされていません。"
        "英語圏のNGワード検出は無効です。"
        "有効にするには: pip install better-profanity"
    )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NG_WORDS_PATH = os.path.join(BASE_DIR, "ng_words.txt")

_ng_words = None


def _normalize(text: str) -> str:
    """
    全角/半角、大文字/小文字などの表記ゆれを吸収する。
    (例: "ＡＢＣ" と "abc" を同じ扱いにする)
    伏字による回避(例: あ*ほ)にはこの正規化だけでは対応できないため、
    より厳密な検出が必要ならmatch関数側の拡張を検討する。
    """
    text = unicodedata.normalize("NFKC", text)
    return text.lower()


def _load_ng_words() -> list[str]:
    global _ng_words
    if _ng_words is not None:
        return _ng_words

    if not os.path.exists(NG_WORDS_PATH):
        print(f"警告: {NG_WORDS_PATH} が見つかりません。ブロックリストは空として扱います。")
        _ng_words = []
        return _ng_words

    words = []
    with open(NG_WORDS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words.append(_normalize(line))

    _ng_words = words
    print(f"NGワードリストを読み込みました: {len(words)}件")
    return _ng_words


def check_blocklist(text: str) -> dict:
    """
    テキストにNGワードが含まれるかチェックする。
    ① 日本語NGワードリスト(ng_words.txt)
    ② better-profanity(英語圏の既製リスト、インストール済みの場合のみ)
    の両方をチェックする。

    Returns:
        dict: {"matched": bool, "matched_words": list[str], "matched_source": list[str]}
    """
    ng_words = _load_ng_words()
    normalized_text = _normalize(text)

    matched = [w for w in ng_words if w and w in normalized_text]
    matched_sources = ["ng_words.txt"] * len(matched)

    if _ENGLISH_FILTER_AVAILABLE and _english_profanity.contains_profanity(text):
        matched.append("[better-profanity該当]")
        matched_sources.append("better-profanity")

    return {
        "matched": len(matched) > 0,
        "matched_words": matched,
        "matched_source": matched_sources,
    }


if __name__ == "__main__":
    test_texts = [
        "サンプルNGワード1が含まれる文",
        "これは普通の文です",
        "This is a normal sentence.",
    ]
    for text in test_texts:
        result = check_blocklist(text)
        print(f"テキスト: {text}")
        print(f"  マッチ: {result['matched']} / 該当語: {result['matched_words']} / ソース: {result['matched_source']}")
