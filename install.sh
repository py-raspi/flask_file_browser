#!/bin/bash

# システムの更新
sudo apt update -y
sudo apt upgrade -y

# 必要なシステムパッケージをインストール
sudo apt install -y \
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
. venv/bin/activate  # 修正: source → .

# pip のアップグレード
pip install --upgrade pip setuptools wheel

# `requirements.txt` から Python ライブラリをインストール
pip install --no-cache-dir -r requirements.txt

# アプリケーションの権限を適切に設定
chmod -R 755 .

echo "インストール完了！"