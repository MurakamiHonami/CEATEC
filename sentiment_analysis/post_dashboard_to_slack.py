"""
生成したダッシュボード画像(dashboard.png)をSlackに投稿するスクリプト

事前準備:
1. https://api.slack.com/apps で新しいSlack Appを作成
2. 「OAuth & Permissions」で Bot Token Scopes に以下を追加:
     - chat:write
     - files:write
3. ワークスペースにインストールし、"Bot User OAuth Token"(xoxb-で始まる)をコピー
4. 投稿したいチャンネルにBotを招待(チャンネル内で /invite @ボット名 )
5. 環境変数に設定:
     setx SLACK_BOT_TOKEN "xoxb-..."       (Windows, 要ターミナル再起動)
     setx SLACK_CHANNEL "#harassment-alert" (チャンネル名 or チャンネルID)

使い方:
    python generate_dashboard.py       (まず画像を生成)
    python post_dashboard_to_slack.py  (Slackに投稿)
"""

import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(BASE_DIR, "dashboard.png")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")


def post_dashboard():
    if not SLACK_BOT_TOKEN:
        print("エラー: 環境変数 SLACK_BOT_TOKEN が設定されていません。")
        return
    if not SLACK_CHANNEL:
        print("エラー: 環境変数 SLACK_CHANNEL が設定されていません。")
        return
    if not os.path.exists(IMAGE_PATH):
        print(f"エラー: {IMAGE_PATH} が見つかりません。先に generate_dashboard.py を実行してください。")
        return

    client = WebClient(token=SLACK_BOT_TOKEN)

    try:
        client.files_upload_v2(
            channel=SLACK_CHANNEL,
            file=IMAGE_PATH,
            title="ハラスメント検出ダッシュボード",
            initial_comment="本日のハラスメント検出状況です。",
        )
        print(f"{SLACK_CHANNEL} に投稿しました。")
    except SlackApiError as e:
        print(f"Slack投稿エラー: {e.response['error']}")


if __name__ == "__main__":
    post_dashboard()
