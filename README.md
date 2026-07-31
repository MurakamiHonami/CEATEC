# ノンデリ検知アプリ

### フロントエンド起動方法
```bash
cd my-app
npm install
npm start
```

### バックエンド起動方法
別のターミナルで
```bash
cd sentiment analysis
py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
※--reload は開発時のみ。本番運用では外すこと。
 モデルロードに時間がかかるため、--reload中の自動再起動のたびに
 再ロードが走る点に注意