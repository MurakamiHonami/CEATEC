"""
predictions_log.csv を集計して、ダッシュボード画像(PNG)を生成するスクリプト(Plotly版)

使い方:
    python generate_dashboard.py
    python generate_dashboard.py --hours 6   (直近6時間だけに絞る場合)
    python generate_dashboard.py --days 7    (直近7日間だけに絞る場合)

必要なライブラリ:
    pip install plotly kaleido
"""

import argparse
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "predictions_log.csv")
OUTPUT_IMAGE_PATH = os.path.join(BASE_DIR, "dashboard.png")

# ---- 配色 ----
COLOR_BG = "#FCFCFC"
COLOR_CARD = "#FCFCFC"
COLOR_PRIMARY = "#B9D5FF"   # 該当なし
COLOR_ACCENT = "#FF7575"    # ハラスメント・侮辱
COLOR_TEXT = "#2D2D3A"
COLOR_SUBTEXT = "#8B8B9E"
COLOR_GRID = "#C3C3D3"
COLOR_PIE_WORD = "#000000"

FONT_FAMILY = "Inter, 'Helvetica Neue', Arial, 'Segoe UI', 'Noto Sans JP', sans-serif"


def load_log(days: int | None, hours: int | None) -> pd.DataFrame:
    try:
        df = pd.read_csv(LOG_PATH)
    except pd.errors.ParserError:
        # 壊れた行(列数がズレている等)があってもスキップして読み込む
        print(
            "警告: predictions_log.csv に列数の合わない行が見つかりました。"
            "該当行をスキップして読み込みます。"
        )
        df = pd.read_csv(LOG_PATH, on_bad_lines="warn", engine="python")

    # utc=True にすることで、データが0件の場合や、書き込み元のタイムゾーンが
    # 混在していても、常にtz-awareなdatetimeとして統一的に扱えるようにする
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    n_invalid = df["timestamp"].isna().sum()
    if n_invalid > 0:
        print(f"警告: timestampが解析できない行が{n_invalid}件あり、除外しました。")
        df = df.dropna(subset=["timestamp"])

    if hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        df = df[df["timestamp"] >= cutoff]
    elif days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        df = df[df["timestamp"] >= cutoff]

    return df


def _generate_empty_state_image(output_path: str, period_label: str):
    """データが0件のときも、Slack投稿などで確実にファイルが存在するよう、
    「まだデータがありません」という空状態の画像を生成する。"""
    fig = go.Figure()
    fig.update_layout(
        title=dict(
            text="ハラスメント検出ダッシュボード",
            subtitle=dict(
                text=f"対象期間: {period_label}　/　総判定件数: 0件",
                font=dict(size=26, color=COLOR_SUBTEXT, weight="bold"),
            ),
            x=0.03, xanchor="left", y=0.85, yanchor="top",
            font=dict(size=45, color=COLOR_TEXT, weight="bold"),
        ),
        font=dict(family=FONT_FAMILY, color=COLOR_TEXT, weight="bold"),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_CARD,
        width=1600,
        height=600,
        margin=dict(l=100, r=100, t=220, b=80),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    fig.add_annotation(
        text="対象期間内にデータがありません",
        x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        font=dict(size=32, color=COLOR_SUBTEXT, weight="bold"),
    )
    fig.write_image(output_path, scale=2)
    print(f"データが0件のため、空状態のダッシュボード画像を {output_path} に保存しました")


def generate_dashboard(df: pd.DataFrame, output_path: str, period_label: str):
    if len(df) == 0:
        print("集計対象のデータがありません。")
        _generate_empty_state_image(output_path, period_label)
        return {
            "total": 0,
            "harassment_count": 0,
            "harassment_ratio": 0.0,
            "avg_confidence": None,
        }

    df = df.copy()
    df["time_bin"] = df["timestamp"].dt.floor("3min")
    df["is_harassment"] = df["label"] == "ハラスメント・侮辱"
    harassment_ratio = df["is_harassment"].mean()

    fig = make_subplots(
        rows=2, cols=2,
        specs=[
            [{"type": "xy"}, {"type": "domain"}],
            [{"type": "table", "colspan": 2}, None],
        ],
        column_widths=[0.5, 0.5],
        row_heights=[0.4, 0.6],
        vertical_spacing=0.16,
        horizontal_spacing=0.10,
        subplot_titles=(f"3分ごとの判定件数({str(datetime.now().day)}日)", "全体の内訳", "検知された文章(最新最大15件)"),
    )

    # ① 3分刻みの判定件数(積み上げ棒グラフ) - (1,1)
    binned = df.groupby(["time_bin", "is_harassment"]).size().unstack(fill_value=0)
    for col, name, color in [
        (False, "該当なし", COLOR_PRIMARY),
        (True, "ハラスメント・侮辱", COLOR_ACCENT),
    ]:
        if col in binned.columns:
            fig.add_trace(
                go.Bar(
                    x=binned.index.strftime("%H:%M"),
                    y=binned[col],
                    name=name,
                    marker_color=color,
                    marker_line_width=0,
                ),
                row=1, col=1,
            )

    # X軸のタイトル、ラベル名の設定
    fig.update_xaxes(
        tickfont=dict(
            size=25  # 目盛り文字のサイズ
        ),
        row=1, col=1  # サブプロットの場所を指定（コード内の row=1, col=1 に合わせる）
    )

    # Y軸のタイトル、ラベル名の設定
    fig.update_yaxes(
        tickfont=dict(
            size=25  # 目盛り文字のサイズ
        ),
        title=dict(
            text="件数",         # 軸の名前
            font=dict(size=25)  # 軸名前のフォントサイズ
        ),
        row=1, col=1
    )

    # ② 全体の円グラフ - (1,2)
    # 凡例は棒グラフ側と重複するため、こちらはオフにする
    counts = df["is_harassment"].value_counts()
    labels = ["ハラスメント・侮辱" if idx else "該当なし" for idx in counts.index]
    colors = [COLOR_ACCENT if idx else COLOR_PRIMARY for idx in counts.index]
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=counts.values,
            hole=0,
            marker=dict(colors=colors, line=dict(color=COLOR_CARD, width=3)),
            textinfo="value+percent",
            textfont=dict(size=28, color=COLOR_PIE_WORD),
            showlegend=False,
        ),
        row=1, col=2,
    )

    # ③ 検知された文章(最新最大15件)の一覧(表) - (2,1)〜(2,2)、最新順、最大15件
    detected = (
        df[df["is_harassment"]]
        .sort_values("timestamp", ascending=False)
        .head(15)
        .copy()
    )
    if len(detected) > 0:
        detected["time_str"] = detected["timestamp"].dt.strftime("%H:%M")
        detected["text_display"] = detected["text"].str.slice(0, 60)
        detected["confidence_display"] = detected["confidence"].apply(lambda c: f"{c:.2f}")

        fig.add_trace(
            go.Table(
                columnwidth=[100, 350],
                header=dict(
                    values=["時刻", "検知された文章(最新最大15件)"],
                    fill_color=COLOR_PRIMARY,
                    font=dict(color="black", size=26, family=FONT_FAMILY, weight="bold"),
                    line=dict(color='gray', width=1),
                    align="center",
                    height=45,
                ),
                cells=dict(
                    values=[
                        detected["time_str"],
                        detected["text_display"],
                    ],
                    fill_color=[[COLOR_CARD, "#D5D5F6"] * len(detected)],
                    font=dict(color=COLOR_TEXT, size=25, family=FONT_FAMILY, weight="bold"),
                    line=dict(color='gray', width=1),
                    align="left",
                    height=42,
                ),
            ),
            row=2, col=1,
        )
    else:
        fig.add_annotation(
            text="対象期間内にハラスメント・侮辱の検知はありませんでした",
            x=0.5, y=0.3, xref="paper", yref="paper", showarrow=False,
            font=dict(size=25, color=COLOR_SUBTEXT, weight="bold"),
        )

    # ダッシュボード全体の設定
    fig.update_layout(
        title=dict(
            text="ハラスメント検出ダッシュボード",
            subtitle=dict(
                text=f"対象期間: {period_label}　/　総判定件数: {len(df)}件",
                font=dict(size=26, color=COLOR_SUBTEXT, weight="bold"),
            ),
            x=0.03, xanchor="left", y=0.98, yanchor="top",
            font=dict(size=45, color=COLOR_TEXT, weight="bold"),
        ),
        font=dict(family=FONT_FAMILY, color=COLOR_TEXT, weight="bold"),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_CARD,
        barmode="stack",
        width=1600,
        height=1700,
        margin=dict(l=100, r=100, t=280, b=80),
        legend=dict(
            orientation="h",       # 横並び
            yanchor="bottom",      # 凡例の下端を基準にする
            y=1.05,                # 💡 1.0より大きくすることでタイトルより上に配置
            xanchor="left",
            x=0,                # メインタイトルと左端を揃える
            font=dict(size=26, color=COLOR_TEXT, weight="bold"), # 大きくなったフォントサイズ
            title_text="",
        ),
        showlegend=True,
    )

    fig.update_xaxes(tickangle=60, gridcolor=COLOR_GRID, linecolor=COLOR_GRID, row=1, col=1)
    fig.update_yaxes(gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, row=1, col=1)

    # サブプロットタイトルを左寄せ・太字風に
    for annotation in fig.layout.annotations:
        if annotation.text in (f"3分ごとの判定件数({str(datetime.now().day)}日)", "全体の内訳", "検知された文章(最新最大15件)"):
            annotation.font = dict(size=35, color=COLOR_TEXT, weight="bold")
            annotation.xanchor = "center"

    fig.write_image(output_path, scale=2)
    print(f"ダッシュボード画像を {output_path} に保存しました")

    return {
        "total": len(df),
        "harassment_count": int(df["is_harassment"].sum()),
        "harassment_ratio": harassment_ratio,
        "avg_confidence": float(df["confidence"].mean()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--days", type=int, default=None, help="直近N日間のデータだけに絞る(省略時は全期間)"
    )
    parser.add_argument(
        "--hours", type=int, default=None, help="直近N時間のデータだけに絞る(3分刻み表示にはこちらが便利)"
    )
    args = parser.parse_args()

    if not os.path.exists(LOG_PATH):
        print(f"{LOG_PATH} が見つかりません。空状態の画像を生成します。")
        _generate_empty_state_image(OUTPUT_IMAGE_PATH, "全期間")
        return

    df = load_log(args.days, args.hours)

    if args.hours:
        period_label = f"直近{args.hours}時間"
    elif args.days:
        period_label = f"直近{args.days}日間"
    else:
        period_label = "全期間"

    n_bins = df["timestamp"].dt.floor("5min").nunique() if len(df) else 0
    if n_bins > 100:
        print(
            f"注意: 3分刻みのビン数が{n_bins}個と多く、グラフが見づらくなる可能性があります。"
            f"--hours で期間を絞ることをおすすめします(例: --hours 6)"
        )

    stats = generate_dashboard(df, OUTPUT_IMAGE_PATH, period_label)
    if stats:
        print("\n--- サマリー ---")
        print(f"総判定件数: {stats['total']}件")
        print(f"ハラスメント・侮辱: {stats['harassment_count']}件 ({stats['harassment_ratio']:.1%})")
        if stats["avg_confidence"] is not None:
            print(f"平均確信度: {stats['avg_confidence']:.4f}")


if __name__ == "__main__":
    main()
