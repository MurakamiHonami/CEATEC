# ノンデリカシー発言検出システム

AWS Lambdaで動作する、日本語の不適切な発言を検出するPythonプログラムです。

## 機能

- HuggingFace Transformersを使用した機械学習ベースの検出
- キーワードベースの検出
- 両方の結果を統合した判定

## ファイル構成

```
nonderi/
├── lambda_function.py   # メインのLambda handler
├── requirements.txt     # Python依存関係
└── README.md           # このファイル
```

## ローカルでのテスト

```bash
# 依存関係のインストール
pip install -r requirements.txt

# テスト実行
python lambda_function.py
```

## Lambda関数の使い方

### 入力形式

#### 単一テキストのチェック
```json
{
  "text": "チェックしたいテキスト"
}
```

#### 複数テキストのチェック
```json
{
  "texts": [
    "テキスト1",
    "テキスト2",
    "テキスト3"
  ]
}
```

### 出力形式

#### 単一テキストの場合
```json
{
  "success": true,
  "result": {
    "text": "お前はバカだ",
    "is_inappropriate": true,
    "confidence": 1.0,
    "reasons": [
      "不適切なキーワードを検出: バカ"
    ],
    "details": {
      "keyword_check": {
        "is_inappropriate": true,
        "found_keywords": ["バカ"],
        "found_patterns": [],
        "confidence": 1.0,
        "method": "keyword-based"
      }
    }
  }
}
```

#### 複数テキストの場合
```json
{
  "success": true,
  "results": [
    {
      "text": "こんにちは",
      "is_inappropriate": false,
      "confidence": 0.0,
      "reasons": ["問題は検出されませんでした"],
      "details": {...}
    },
    {
      "text": "バカ野郎",
      "is_inappropriate": true,
      "confidence": 1.0,
      "reasons": ["不適切なキーワードを検出: バカ"],
      "details": {...}
    }
  ]
}
```

## AWS Lambdaへのアップロード

### 方法1: Lambdaレイヤーを使用（推奨）

transformersとtorchは大きいため、Lambdaレイヤーとして作成することを推奨します。

1. 依存関係をパッケージ化:
```bash
mkdir python
pip install -r requirements.txt -t python/
zip -r layer.zip python/
```

2. Lambdaレイヤーを作成してアップロード

3. lambda_function.pyをLambda関数としてアップロード

### 方法2: Dockerコンテナイメージを使用

大きな依存関係がある場合、コンテナイメージの使用も検討できます。

### 方法3: 簡易版（キーワードベースのみ）

機械学習モデルを使わず、キーワードベースのみで動作させる場合:
- lambda_function.pyの`initialize_model()`を呼ばない
- キーワードチェックのみで判定

この場合、requirements.txtは不要になります。

## 環境変数

- `MODEL_NAME`: 使用するHuggingFaceモデル名（デフォルト: `line-corporation/line-distilbert-base-japanese`）

## カスタマイズ

### キーワードリストの変更

`lambda_function.py`の`check_keywords()`関数内の`inappropriate_keywords`と`discriminatory_patterns`を編集してください。

### モデルの変更

日本語の感情分析や有害コンテンツ検出用の他のモデルを使用できます:
- `cl-tohoku/bert-base-japanese-sentiment`
- `line-corporation/line-distilbert-base-japanese`
- その他のHuggingFace日本語モデル

## 注意事項

- 初回実行時はモデルのダウンロードが発生するため、時間がかかります
- Lambdaのメモリは最低1024MB以上を推奨
- タイムアウトは30秒以上を推奨
- Lambda Layersまたはコンテナイメージの使用を強く推奨（パッケージサイズが大きいため）

## ライセンス

MIT License
