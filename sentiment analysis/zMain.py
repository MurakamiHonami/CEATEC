"""
ハラスメント検出API (FastAPI)

フロントエンド(WebSpeechで音声認識した文字列)からPOSTされたテキストを、
①NGワードブロックリスト → ②BERTアンサンブルモデル の順で判定し、結果を返す。

起動方法:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

(--reload は開発時のみ。本番運用では外すこと。
 モデルロードに時間がかかるため、--reload中の自動再起動のたびに
 再ロードが走る点に注意)

エンドポイント:
    POST /result
        body: {"text": "分析したいテキスト"}
        response: {
            "is_harassment": bool,
            "label": str,
            "confidence": float,
            "source": str,          # "blocklist" or "bert_ensemble"
            "individual_seeds": [...]  # デバッグ用、シードごとの内訳
        }

    GET /health
        起動確認・モデルロード済みかの確認用
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ensemble_inference import predict_ensemble, _load_models
from blocklist_filter import check_blocklist

_model_ready = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時に一度だけモデルをロードしておく(リクエストのたびにロードすると遅すぎるため)
    global _model_ready
    print("モデルをロード中...")
    _load_models()
    _model_ready = True
    print("モデルロード完了。リクエスト受付可能です。")
    yield
    # (終了時に何か片付けが必要ならここに書く)


app = FastAPI(title="ハラスメント検出API", lifespan=lifespan)

# フロントエンドが別オリジンから叩く前提のCORS設定
# 本番運用では allow_origins をフロントエンドの実際のドメインに限定すること
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 例: ["https://your-frontend.example.com"]
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    is_harassment: bool
    label: str
    confidence: float
    source: str
    individual_seeds: list | None = None


@app.get("/health")
def health():
    return {"status": "ok", "model_ready": _model_ready}


@app.post("/result", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    text = req.text.strip()

    if not text:
        return AnalyzeResponse(
            is_harassment=False, label="該当なし", confidence=1.0, source="empty_input"
        )

    # ① NGワードブロックリストを先にチェック(高速・確実)
    blocklist_result = check_blocklist(text)
    if blocklist_result["matched"]:
        return AnalyzeResponse(
            is_harassment=True,
            label="ハラスメント・侮辱",
            confidence=1.0,
            source=f"blocklist({','.join(blocklist_result['matched_source'])})",
        )

    # ② ヒットしなければBERTアンサンブルで文脈判定
    result = predict_ensemble(text, verbose=True)
    is_harassment = result["label"] == "ハラスメント・侮辱"

    return AnalyzeResponse(
        is_harassment=is_harassment,
        label=result["label"],
        confidence=result["confidence"],
        source="bert_ensemble",
        individual_seeds=result.get("individual_predictions"),
    )
