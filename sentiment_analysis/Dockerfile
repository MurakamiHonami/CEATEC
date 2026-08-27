FROM python:3.12-slim

# uv 本体をコピー（インストール不要・単一バイナリ）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

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

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
