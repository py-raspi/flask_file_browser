# Flask File Browser - Raspberry Pi NAS

Flaskを用いたシンプルな画像・動画ビューア。Raspberry Piに接続したストレージ内のファイルを閲覧・管理できます。

Tailscaleを使用したVPN接続、およびSambaによるファイル共有機能を備えており、外出先からもアクセス・操作が可能です。**本プロジェクトではTailscaleの無料プランを使用します。**

---

## 🚀 概要

- `sudo` 権限を使用します。
- 環境変数は `env.env` に設定してください。
- Sambaの共有名や共有ディレクトリは、ご自身の環境に合わせて適宜変更してください。

## 📌 使用技術・ライブラリ

### FontAwesome
本プロジェクトでは、[FontAwesome Free](https://fontawesome.com/) の **Free版Kit** を利用しています。

- **ライセンス**: MITライセンス ([詳細はこちら](https://github.com/FortAwesome/Font-Awesome/blob/6.x/LICENSE.txt))
- **利用条件**: 商用・非商用を問わず利用可能
- **KitのURL**: 本リポジトリには含まれていません。各自で[公式サイト](https://fontawesome.com/)より取得してください。

---

## 📜 ライセンスについて

本プロジェクトのソースコードは **MITライセンス** のもとで提供されます。

### 外部ソフトウェア
ファイル共有機能のために **Samba** を利用しています。
- Samba自体は **GPLv3ライセンス** で提供されていますが、本プロジェクトでは **設定ファイルのみを提供** し、本体の改変は行っていません。
- 詳細は [Samba公式サイト](https://www.samba.org/) をご確認ください。

---

## 🛠 インストール

### 1️⃣ リポジトリのクローン
```sh
git clone https://github.com/py-raspi/flask_file_browser.git
cd flask_file_browser
sudo sh install.sh
```

### 2️⃣ Sambaのセットアップ
共有ディレクトリは環境に合わせて変更してください:
```sh
sudo apt update
sudo mkdir shared
sudo chmod 777 shared
sudo apt install samba
```

#### 📄 Samba 設定ファイル (`/etc/samba/smb.conf`)
以下を `[global]` に追加:
```ini
browseable = no
min protocol = SMB2
max protocol = SMB3
unix extensions = no
vfs objects = catia fruit streams_xattr
```

共有フォルダ設定を末尾に追加（環境に合わせて変更してください）:
```ini
[YourShareName]
   path = /your/custom/path
   browseable = yes
   writable = yes
   create mask = 0777
   directory mask = 0777
   force user = your_user
   force group = your_group
   preserve case = yes
   short preserve case = yes
   dos filetimes = yes
   store dos attributes = yes
   nt acl support = yes
   fruit:encoding = native
   fruit:metadata = stream
   fruit:resource = file
   fruit:nfs_aces = no
   fruit:aapl = no
   ea support = yes
   streams_xattr:prefix = user.
   mangled names = yes
   case sensitive = no
   veto files = /lost+found/
   hide files = /lost+found/
   hide dot files = yes
```

Sambaを再起動:
```sh
sudo systemctl restart smbd
sudo smbpasswd -a your_user
```

### 3️⃣ Tailscaleのセットアップ
[無料アカウント](https://tailscale.com/) を作成し、以下を実行:
```sh
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --accept-dns=true
tailscale ip -4
```

---

## ⚙ 設定ファイルの編集

### `env.env`
```ini
SSD_UUID=***********************
SHARED_FOLDER=/your/custom/path
VENV_PATH=/home/pi/flask_file_browser/venv
SYNC_DB_AND_THUMBNAILS=/home/pi/flask_file_browser/sync_db_and_thumbnails.py
PORT=7001
```

### `templates/index.html`
FontAwesomeのKit URLを適宜設定:
```html
<script src="" crossorigin="anonymous"></script>
```

---

## ✅ 動作確認
仮想環境を有効化し、アプリを起動:
```sh
source venv/bin/activate
python3 app.py
```

---

## 🔄 自動起動設定 (systemd)

`/usr/lib/systemd/system/flask_file_browser.service` を作成:
```ini
[Unit]
Description=Flask File Browser Service
After=network.target

[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/flask_file_browser
ExecStart=/home/pi/flask_file_browser/venv/bin/gunicorn -w 4 -b 0.0.0.0:7001 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

サービスを有効化:
```sh
sudo systemctl start flask_file_browser
sudo systemctl enable flask_file_browser
```

---

## 🔗 アクセス方法

### 1️⃣ Flaskアプリ
```
http://your_host:7001/
```

### 2️⃣ Samba (Windowsエクスプローラー)
```
\\your_host\YourShareName
```

---

## 🎉 動作イメージ

![Image1](https://github.com/user-attachments/assets/95b688a7-14d9-4574-bf9d-f2371c2d4252)
![Image2](https://github.com/user-attachments/assets/15710d96-689a-4afd-81a8-5b0a48557327)
![Image3](https://github.com/user-attachments/assets/006ede7a-d834-4ae6-b5dc-675caa9bf7a8)
![Image4](https://github.com/user-attachments/assets/7c173faf-c25d-434e-aa76-902a2691bfc3)
![Image5](https://github.com/user-attachments/assets/17d299e0-d4f0-481f-ace1-c2e88c2601ca)
![Image6](https://github.com/user-attachments/assets/1e473489-3ab5-4ba7-bc6f-c4901ba9370e)

---

## 📜 ライセンス
MIT License © 2025 py-raspi  
詳細は [LICENSE](LICENSE) を参照してください。

