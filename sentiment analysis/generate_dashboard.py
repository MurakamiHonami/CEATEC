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
COLOR_BG = "#EEF0FB"
COLOR_CARD = "#FFFFFF"
COLOR_PRIMARY = "#6C5CE7"   # 該当なし
COLOR_ACCENT = "#F0932B"    # ハラスメント・侮辱
COLOR_TEXT = "#2D2D3A"
COLOR_SUBTEXT = "#8B8B9E"
COLOR_GRID = "#E4E4F0"

FONT_FAMILY = "Yu Gothic, Meiryo, MS Gothic, sans-serif"


def load_log(days: int | None, hours: int | None) -> pd.DataFrame:
    df = pd.read_csv(LOG_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    if hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        df = df[df["timestamp"] >= cutoff]
    elif days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        df = df[df["timestamp"] >= cutoff]

    return df


def generate_dashboard(df: pd.DataFrame, output_path: str, period_label: str):
    if len(df) == 0:
        print("集計対象のデータがありません。")
        return None

    df = df.copy()
    df["time_bin"] = df["timestamp"].dt.floor("5min")
    df["is_harassment"] = df["label"] == "ハラスメント・侮辱"
    harassment_ratio = df["is_harassment"].mean()

    fig = make_subplots(
        rows=2, cols=2,
        specs=[
            [{"type": "xy", "colspan": 2}, None],
            [{"type": "domain"}, {"type": "xy"}],
        ],
        row_heights=[0.55, 0.45],
        vertical_spacing=0.22,
        horizontal_spacing=0.12,
        subplot_titles=("5分ごとの判定件数", "全体の内訳", "確信度の分布"),
    )

    # ① 5分刻みの判定件数(積み上げ棒グラフ)
    binned = df.groupby(["time_bin", "is_harassment"]).size().unstack(fill_value=0)
    for col, name, color in [
        (False, "該当なし", COLOR_PRIMARY),
        (True, "ハラスメント・侮辱", COLOR_ACCENT),
    ]:
        if col in binned.columns:
            fig.add_trace(
                go.Bar(
                    x=binned.index.strftime("%m/%d %H:%M"),
                    y=binned[col],
                    name=name,
                    marker_color=color,
                    marker_line_width=0,
                ),
                row=1, col=1,
            )

    # ② 全体の内訳(ドーナツグラフ)
    counts = df["is_harassment"].value_counts()
    labels = ["ハラスメント・侮辱" if idx else "該当なし" for idx in counts.index]
    colors = [COLOR_ACCENT if idx else COLOR_PRIMARY for idx in counts.index]
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=counts.values,
            hole=0.65,
            marker=dict(colors=colors, line=dict(color=COLOR_CARD, width=3)),
            textinfo="none",
            showlegend=True,
        ),
        row=2, col=1,
    )
    fig.add_annotation(
        text=f"{harassment_ratio:.0%}",
        x=0.205, y=0.22, xref="paper", yref="paper", showarrow=False,
        font=dict(size=30, color=COLOR_ACCENT), xanchor="center",
    )
    fig.add_annotation(
        text="ハラスメント比率",
        x=0.205, y=0.16, xref="paper", yref="paper", showarrow=False,
        font=dict(size=12, color=COLOR_SUBTEXT), xanchor="center",
    )

    # ③ 確信度の分布(ヒストグラム)
    fig.add_trace(
        go.Histogram(
            x=df["confidence"],
            nbinsx=20,
            marker_color=COLOR_PRIMARY,
            marker_line_color=COLOR_CARD,
            marker_line_width=1,
            showlegend=False,
        ),
        row=2, col=2,
    )
    fig.add_shape(
        type="rect", x0=0.55, x1=0.70, y0=0, y1=1,
        xref="x2", yref="y2 domain",
        fillcolor=COLOR_ACCENT, opacity=0.15, line_width=0,
        row=2, col=2,
    )
    fig.add_annotation(
        x=0.55, y=1, xref="x2", yref="y2 domain",
        text="境界事例の目安", showarrow=False,
        font=dict(size=10, color=COLOR_SUBTEXT),
        xanchor="left", yanchor="bottom",
        row=2, col=2,
    )

    fig.update_layout(
        title=dict(
            text="ハラスメント検出ダッシュボード",
            subtitle=dict(
                text=f"対象期間: {period_label}　/　総判定件数: {len(df)}件",
                font=dict(size=13, color=COLOR_SUBTEXT),
            ),
            x=0.03, xanchor="left", y=0.98, yanchor="top",
            font=dict(size=24, color=COLOR_TEXT),
        ),
        font=dict(family=FONT_FAMILY, color=COLOR_TEXT),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_CARD,
        barmode="stack",
        width=1400,
        height=1000,
        margin=dict(l=60, r=60, t=190, b=60),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
            font=dict(size=11, color=COLOR_SUBTEXT), title_text="",
        ),
    )
    fig.update_xaxes(tickangle=60, gridcolor=COLOR_GRID, linecolor=COLOR_GRID, row=1, col=1)
    fig.update_yaxes(gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, row=1, col=1)
    fig.update_xaxes(gridcolor=COLOR_GRID, linecolor=COLOR_GRID, row=2, col=2)
    fig.update_yaxes(gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, row=2, col=2)

    # サブプロットタイトルを左寄せ・太字風に
    for annotation in fig.layout.annotations:
        if annotation.text in ("5分ごとの判定件数", "全体の内訳", "確信度の分布"):
            annotation.font = dict(size=15, color=COLOR_TEXT)
            annotation.xanchor = "left"

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
        "--hours", type=int, default=None, help="直近N時間のデータだけに絞る(5分刻み表示にはこちらが便利)"
    )
    args = parser.parse_args()

    if not os.path.exists(LOG_PATH):
        print(f"{LOG_PATH} が見つかりません。まだAPIへのリクエストがないか、パスが違います。")
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
            f"注意: 5分刻みのビン数が{n_bins}個と多く、グラフが見づらくなる可能性があります。"
            f"--hours で期間を絞ることをおすすめします(例: --hours 6)"
        )

    stats = generate_dashboard(df, OUTPUT_IMAGE_PATH, period_label)
    if stats:
        print("\n--- サマリー ---")
        print(f"総判定件数: {stats['total']}件")
        print(f"ハラスメント・侮辱: {stats['harassment_count']}件 ({stats['harassment_ratio']:.1%})")
        print(f"平均確信度: {stats['avg_confidence']:.4f}")


if __name__ == "__main__":
    main()