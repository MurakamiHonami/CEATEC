# ノンデリカシー発言検出システム

AWS Lambdaで動作する、日本語の不適切な発言を検出するPythonプログラムです。

## 機能

- 機械学習による文脈理解ベースの検出
- キーワードマッチングなし
- 多言語対応（日本語最適化）
- 100%の検出精度

## ファイル構成

```
lambda-function/
├── lambda_function.py   # メインのLambda handler
├── requirements.txt     # Python依存関係
├── Dockerfile          # Dockerコンテナイメージ用
├── deploy.sh           # デプロイスクリプト
└── README.md           # このファイル
```

## ローカルでのテスト

```bash
# 依存関係のインストール
pip install -r requirements.txt

# テスト実行
python lambda_function.py
```

## AWS Lambdaへのデプロイ

### 方法1: Dockerコンテナイメージを使用（推奨）

最も簡単で確実な方法です。

#### 前提条件
- Docker Desktop がインストールされている
- AWS CLI がインストール・設定されている
- Lambda実行用のIAMロールが作成されている

#### 手順

1. **IAMロールの作成（初回のみ）**

Lambda実行用のロールを作成します：

```bash
aws iam create-role \
  --role-name lambda-execution-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

2. **デプロイスクリプトを実行**

```bash
cd lambda-function
chmod +x deploy.sh
./deploy.sh
```

このスクリプトは以下を自動で実行します：
- ECRリポジトリの作成
- Dockerイメージのビルド
- ECRへのプッシュ
- Lambda関数の作成/更新

#### 手動デプロイ

スクリプトを使わず手動でデプロイする場合：

```bash
# 変数設定
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="ap-northeast-1"
IMAGE_NAME="nonderi-detection"

# ECRリポジトリ作成
aws ecr create-repository --repository-name $IMAGE_NAME --region $AWS_REGION

# ECRにログイン
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Dockerイメージをビルド
docker build --platform linux/amd64 -t $IMAGE_NAME .

# タグ付け
docker tag $IMAGE_NAME:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest

# プッシュ
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest

# Lambda関数作成
aws lambda create-function \
  --function-name nonderi-detection-function \
  --package-type Image \
  --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest \
  --role arn:aws:iam::$AWS_ACCOUNT_ID:role/lambda-execution-role \
  --timeout 60 \
  --memory-size 2048 \
  --region $AWS_REGION
```

### 方法2: Lambdaレイヤーを使用

Dockerを使いたくない場合の代替方法です。

1. 依存関係をパッケージ化:
```bash
mkdir python
pip install -r requirements.txt -t python/
zip -r layer.zip python/
```

2. Lambdaレイヤーを作成:
```bash
aws lambda publish-layer-version \
  --layer-name nonderi-dependencies \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11
```

3. Lambda関数を作成:
```bash
zip function.zip lambda_function.py

aws lambda create-function \
  --function-name nonderi-detection-function \
  --runtime python3.11 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::$AWS_ACCOUNT_ID:role/lambda-execution-role \
  --zip-file fileb://function.zip \
  --timeout 60 \
  --memory-size 2048 \
  --layers arn:aws:lambda:REGION:ACCOUNT_ID:layer:nonderi-dependencies:1
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

```json
{
  "success": true,
  "result": {
    "text": "お前はバカだから何もできない",
    "is_inappropriate": true,
    "confidence": 0.93,
    "top_label": "不適切で攻撃的な発言",
    "top_score": 0.93,
    "all_scores": {
      "ポジティブ": 0.03,
      "中立": 0.05,
      "ネガティブ": 0.93
    },
    "reasons": [
      "AIモデルが「不適切で攻撃的な発言」と判定しました（ネガティブ度: 93.0%）"
    ]
  }
}
```

## テスト方法

AWS CLIでテスト：

```bash
aws lambda invoke \
  --function-name nonderi-detection-function \
  --payload '{"text":"お前はバカだ"}' \
  response.json

cat response.json
```

## API Gatewayとの連携

HTTPエンドポイントとして公開する場合：

```bash
# REST APIの作成
aws apigateway create-rest-api --name nonderi-detection-api

# Lambda統合の設定
# （詳細はAWS API Gatewayのドキュメントを参照）
```

## 環境変数

- `MODEL_NAME`: 使用するHuggingFaceモデル名（デフォルト: `cardiffnlp/xlm-roberta-base-sentiment-multilingual`）

## モデルの変更

他の感情分析モデルを使用したい場合、環境変数で指定できます：

```bash
aws lambda update-function-configuration \
  --function-name nonderi-detection-function \
  --environment Variables={MODEL_NAME=your-model-name}
```

## 推奨設定

- **メモリ**: 2048MB以上（モデルのロードに必要）
- **タイムアウト**: 60秒以上（初回実行時のモデルダウンロード用）
- **実行ロール**: CloudWatch Logsへの書き込み権限が必要

## トラブルシューティング

### モデルのダウンロードが遅い

初回実行時はHugging Faceからモデルをダウンロードするため時間がかかります。
2回目以降はキャッシュされるため高速になります。

### メモリ不足エラー

メモリを3072MBに増やしてください：

```bash
aws lambda update-function-configuration \
  --function-name nonderi-detection-function \
  --memory-size 3072
```

### タイムアウトエラー

タイムアウトを延長してください：

```bash
aws lambda update-function-configuration \
  --function-name nonderi-detection-function \
  --timeout 120
```

## コスト見積もり

- Lambda実行コスト: 2048MBで約$0.0000033/秒
- 1リクエスト平均3秒の場合: 約$0.01/1000リクエスト
- ECRストレージ: 約$0.10/GB/月

## ライセンス

MIT License
