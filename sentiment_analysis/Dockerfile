FROM python:3.12-slim

# uv を pip で導入（ghcr.io からの取得が不要になり、認証エラーを回避）
RUN pip install --no-cache-dir uv

WORKDIR /app

# UV_LINK_MODE=copy: cache mount とレイヤ間で hardlink が張れない警告を回避
# UV_COMPILE_BYTECODE=1: .pyc を事前生成して起動を短縮
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

COPY requirements.txt .

# torch は PyPI のデフォルトが CUDA 同梱で nvidia-* を大量に引くため、
# CPU 専用インデックスから先に入れて後段の解決対象から外す
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system \
        --index-url https://download.pytorch.org/whl/cpu \
        torch

# 残りの依存（torch は充足済みなので再取得されない）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

# kaleido v1 は PNG 出力に Chrome/Chromium の実行ファイルを必要とする。
# slim イメージには入っていないため apt で chromium を入れ、
# choreographer(kaleido の依存)が最優先で見る BROWSER_PATH で明示的に指す。
# fonts-noto-cjk はグラフ内の日本語ラベルが豆腐(□)になるのを防ぐため。
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

ENV BROWSER_PATH=/usr/bin/chromium

# --- COPY をレイヤ分割する ---
# モデル(大容量)を先に、独立したレイヤとして入れる。
# コードだけ編集した場合、この層はキャッシュが効いて再コピー・再exportされない。
COPY harassment_classifier_seed42/ ./harassment_classifier_seed42/
COPY harassment_classifier_seed123/ ./harassment_classifier_seed123/
COPY harassment_classifier_seed2024/ ./harassment_classifier_seed2024/

# コード・設定(小容量)。頻繁に変わるのでレイヤの最後に置く
COPY *.py *.csv *.txt ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
