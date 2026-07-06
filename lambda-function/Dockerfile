FROM public.ecr.aws/lambda/python:3.11

# 依存関係をコピー
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# Lambda関数のコードをコピー
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Lambda handlerを指定
CMD ["lambda_function.lambda_handler"]
