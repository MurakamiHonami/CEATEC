#!/bin/bash

# AWSアカウントIDとリージョンを設定
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="ap-northeast-1"  # 東京リージョン
IMAGE_NAME="nonderi-detection"
FUNCTION_NAME="nonderi-detection-function"

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"

# ECRリポジトリを作成（既に存在する場合はスキップ）
echo "Creating ECR repository..."
aws ecr create-repository --repository-name $IMAGE_NAME --region $AWS_REGION 2>/dev/null || echo "Repository already exists"

# ECRにログイン
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Dockerイメージをビルド
echo "Building Docker image..."
docker build --platform linux/amd64 -t $IMAGE_NAME .

# イメージにタグを付ける
echo "Tagging image..."
docker tag $IMAGE_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest

# ECRにプッシュ
echo "Pushing to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest

# Lambda関数を作成または更新
echo "Creating/Updating Lambda function..."
FUNCTION_EXISTS=$(aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>/dev/null)

if [ -z "$FUNCTION_EXISTS" ]; then
    echo "Creating new Lambda function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest \
        --role arn:aws:iam::$AWS_ACCOUNT_ID:role/lambda-execution-role \
        --timeout 60 \
        --memory-size 2048 \
        --region $AWS_REGION
else
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME:latest \
        --region $AWS_REGION
fi

echo "Deployment complete!"
echo "Function ARN: arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:$FUNCTION_NAME"
