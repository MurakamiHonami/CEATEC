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
    POST /api/check-nondeli
        body: {"text": "分析したいテキスト"}
        response: {
            "is_nondeli": bool,
            "label": str,
            "confidence": float,
            "reason": str,          # "blocklist(...)" or "bert_ensemble"
            "individual_seeds": [...]  # デバッグ用、シードごとの内訳
        }

    GET /health
        起動確認・モデルロード済みかの確認用

    POST /api/send-dashboard
        body: なし
        response: {"success": bool, "message": str}
        generate_dashboard.py -> post_dashboard_to_slack.py を実行し、
        ダッシュボード画像をSlackに投稿する
"""

from contextlib import asynccontextmanager
import csv
import os
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ensemble_inference import predict_ensemble, _load_models
from blocklist_filter import check_blocklist

_model_ready = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "predictions_log.csv")
LOG_FIELDNAMES = ["timestamp", "text", "label", "confidence", "source"]
GENERATE_SCRIPT = os.path.join(BASE_DIR, "generate_dashboard.py")
POST_SCRIPT = os.path.join(BASE_DIR, "post_dashboard_to_slack.py")
DASHBOARD_IMAGE_PATH = os.path.join(BASE_DIR, "dashboard.png")


def log_prediction(text: str, label: str, confidence: float, source: str):
    """判定結果をCSVに1件ずつ追記する(ダッシュボード生成用のログ)"""
    file_exists = os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds"),
                "text": text,
                "label": label,
                "confidence": round(confidence, 4),
                "source": source,
            }
        )


def run_generate_dashboard(hours: int | None = None) -> tuple[bool, str]:
    """generate_dashboard.py をサブプロセスで実行する。成功可否とメッセージを返す。"""
    cmd = [sys.executable, GENERATE_SCRIPT]
    if hours is not None:
        cmd += ["--hours", str(hours)]

    result = subprocess.run(
        cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print("generate_dashboard.py エラー:", result.stderr)
        return False, f"ダッシュボード画像の生成に失敗しました: {result.stderr[-300:]}"
    return True, "生成成功"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時に一度だけモデルをロードしておく(リクエストのたびにロードすると遅すぎるため)
    global _model_ready

    # 起動時に過去の発言履歴を削除する(ヘッダーのみのCSVに戻す)
    # LOG_PATH(絶対パス)を使うこと。相対パスだと起動時のカレントディレクトリ次第で
    # 別のファイルを作ってしまい、本来リセットしたいファイルが変わらない事故が起きる
    with open(LOG_PATH, "w", newline="", encoding="utf-8-sig") as f:
        f.write(",".join(LOG_FIELDNAMES) + "\n")
    print("過去の履歴を削除しました")

    # 過去のダッシュボード画像も削除する
    # (データが0件だとgenerate_dashboard.pyは何もしないため、
    #  ここで明示的に消さないと古い画像がそのまま残ってしまう)
    if os.path.exists(DASHBOARD_IMAGE_PATH):
        os.remove(DASHBOARD_IMAGE_PATH)
        print("過去のダッシュボード画像を削除しました")

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
    is_nondeli: bool
    label: str
    confidence: float
    reason: str
    individual_seeds: list | None = None


class SendDashboardResponse(BaseModel):
    success: bool
    message: str


@app.get("/health")
def health():
    return {"status": "ok", "model_ready": _model_ready}


@app.post("/api/check-nondeli", response_model=AnalyzeResponse)
def check_nondeli(req: AnalyzeRequest):
    text = req.text.strip()

    if not text:
        return AnalyzeResponse(
            is_nondeli=False, label="該当なし", confidence=1.0, reason="empty_input"
        )

    # ① NGワードブロックリストを先にチェック(高速・確実)
    blocklist_result = check_blocklist(text)
    if blocklist_result["matched"]:
        reason = f"blocklist({','.join(blocklist_result['matched_source'])})"
        log_prediction(text, "ハラスメント・侮辱", 1.0, reason)
        return AnalyzeResponse(
            is_nondeli=True,
            label="ハラスメント・侮辱",
            confidence=1.0,
            reason=reason,
        )

    # ② ヒットしなければBERTアンサンブルで文脈判定
    result = predict_ensemble(text, verbose=True)
    is_nondeli = result["label"] == "ハラスメント・侮辱"
    log_prediction(text, result["label"], result["confidence"], "bert_ensemble")

    return AnalyzeResponse(
        is_nondeli=is_nondeli,
        label=result["label"],
        confidence=result["confidence"],
        reason="bert_ensemble",
        individual_seeds=result.get("individual_predictions"),
    )


@app.post("/api/send-dashboard", response_model=SendDashboardResponse)
def send_dashboard():
    """
    generate_dashboard.py -> post_dashboard_to_slack.py を順番に実行する。
    フロントの「送信中...」ボタンから呼ばれる想定の同期エンドポイント
    (完了までレスポンスを返さないので、ボタン側は結果を待って表示を戻す)。
    """

    # ① ダッシュボード画像を生成(直近24時間分)
    success, message = run_generate_dashboard(hours=24)
    if not success:
        return SendDashboardResponse(success=False, message=message)

    # ② 生成した画像をSlackに投稿
    result = subprocess.run(
        [sys.executable, POST_SCRIPT],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print("post_dashboard_to_slack.py エラー:", result.stderr)
        return SendDashboardResponse(
            success=False,
            message=f"Slackへの投稿に失敗しました: {result.stderr[-300:]}",
        )

    return SendDashboardResponse(success=True, message="Slackに送信しました")