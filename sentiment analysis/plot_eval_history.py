"""
eval_history.csv を見やすく可視化するスクリプト

- コンソールに整形した表を表示
- accuracy / precision / recall / f1 の推移を折れ線グラフにして
  eval_history_plot.png として保存

使い方:
    pip install matplotlib pandas --break-system-packages
    python plot_eval_history.py
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# 日本語文字化け対策（Windows環境向け、Macの場合は "Hiragino Sans" などに変更）
matplotlib.rcParams["font.family"] = "MS Gothic"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(BASE_DIR, "eval_history.csv")
PLOT_PATH = os.path.join(BASE_DIR, "eval_history_plot.png")


def main():
    if not os.path.exists(HISTORY_PATH):
        print(f"{HISTORY_PATH} が見つかりません。まず evaluate_model.py を実行してください。")
        return

    df = pd.read_csv(HISTORY_PATH)

    if len(df) == 0:
        print("eval_history.csv にまだデータがありません。")
        return

    # ---- 1. 見やすい表をコンソールに表示 ----
    print("=" * 70)
    print("評価履歴")
    print("=" * 70)
    display_df = df.copy()
    display_df["timestamp"] = pd.to_datetime(display_df["timestamp"]).dt.strftime("%m/%d %H:%M")
    print(display_df.to_string(index=False))

    # 直近との差分も表示（前回より良くなったか一目で分かる）
    if len(df) >= 2:
        print("\n直近の変化:")
        for col in ["accuracy", "precision", "recall", "f1"]:
            diff = df[col].iloc[-1] - df[col].iloc[-2]
            arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
            print(f"  {col}: {diff:+.4f} {arrow}")

    # ---- 2. グラフを保存 ----
    fig, ax = plt.subplots(figsize=(9, 5))

    x = range(len(df))
    for col, marker in zip(
        ["accuracy", "precision", "recall", "f1"], ["o", "s", "^", "d"]
    ):
        ax.plot(x, df[col], marker=marker, label=col)

    ax.set_xticks(list(x))
    ax.set_xticklabels(df["train_data_size"], rotation=0)
    ax.set_xlabel("学習データ件数 (train_data_size)")
    ax.set_ylabel("スコア")
    ax.set_ylim(0, 1)
    ax.set_title("学習データ量ごとの精度推移")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(PLOT_PATH, dpi=150)
    print(f"\nグラフを {PLOT_PATH} に保存しました")


if __name__ == "__main__":
    main()
