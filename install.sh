#!/bin/bash
# MIT License (c) 2025 py-raspi
# See LICENSE for details.

set -e

# システムの更新
sudo apt update && sudo apt upgrade -y

# 必要なシステムパッケージをインストール
sudo apt install --no-install-recommends -y \
    ffmpeg \
    sqlite3 \
    python3 \
    python3-venv \
    python3-pip

# 仮想環境の作成
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 仮想環境を有効化
. venv/bin/activate

# pip のアップグレード
pip install --upgrade pip setuptools wheel

# `requirements.txt` から Python ライブラリをインストール
if [ -f "requirements.txt" ]; then
    pip install --no-cache-dir -r requirements.txt
else
    echo "requirements.txt が見つかりません。"
fi

# アプリケーションの権限を適切に設定
chmod -R u+rwx,g+rx,o+rx .

echo "インストール完了！"
