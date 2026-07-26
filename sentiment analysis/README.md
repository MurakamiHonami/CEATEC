# 感情分析モデル

## 作成途中なのでディレクトリ汚いです

### 使用方法
1.raw_texts.txtに文章を挿入、続けて文章を挿入しない
2.manual_label.pyで判別
3.train_harassment_classifier.pyで学習
4.inference_harassment_classifier.pyでテスト
5.evaluate_model.pyで正答率、再現率、適性率、F1など確認
6.plot_eval_history.pyで図表確認
7.run_multi_seed_experiment.pyで設定した各SEEDの正答率、再現率、適性率、F1確認

## Google ColabでT４ GPUを使用する方法
1.GPU確認：torch.cuda.is_available() が True になるか確認
2.ライブラリインストール：transformers, datasets, scikit-learn, accelerate
3.ファイルアップロード：train_harassment_classifier.py / evaluate_model.py / run_multi_seed_experiment.py / labeled_data.csv / eval_samples.csv をまとめて選択してアップロード
4.学習実行：普段通り train_harassment_classifier.py を実行するだけです。GPUがあれば transformers のTrainerが自動で使ってくれるので、コードは一切変更不要です
5.評価実行：evaluate_model.py
6.モデルのダウンロード：harassment_classifier/final フォルダをzip化してローカルPCにダウンロード
7.（おまけ）eval_history.csv / multi_seed_results.csv もダウンロード可能

ダウンロードしたzipを解凍して、ローカルの harassment_classifier/final に置き換えれば、これまで通り inference_harassment_classifier.py などがそのまま使えます。