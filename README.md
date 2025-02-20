# img & mov viewer
RaspberryPiに接続したストレージ内の画像・動画を閲覧できるFlask Appです。
<br />
TailscaleでVPNに接続し、Samba共有も行うため、外出先からでもアクセス・ファイル操作が可能です。

## introduction
* <code>sudo</code>を使用します。
* ユーザーが<code>env.env</code>に環境変数を設定する必要があります

## clone
```
git clone https://github.com/py-raspi/flask_file_browser.git
```
```
cd flask_file_browser
```
```
sudo sh install.sh
```

## install

### Samba
```
sudo apt update
```
```
sudo mkdir shared
```
```
sudo chmod 777 shared
```
```
sudo apt install samba
```
```
sudo nano /etc/samba/smb.conf
```
Sambaの設定ファイルを編集する
```
#[global]に以下を追記
   browseable=no

   ## SMB3を優先（古いクライアントがいなければ）
   min protocol = SMB2
   max protocol = SMB3

   unix extensions = no
   vfs objects = catia fruit streams_xattr
```
```
#末尾に以下を記述
[Pi5]
   path = /home/pi/shared
   browseable = yes
   writable = yes
   create mask = 0777
   directory mask = 0777
   force user = pi
   force group = pi
   preserve case = yes
   short preserve case = yes
   dos filetimes = yes
   store dos attributes = yes
   nt acl support = yes

   # Windows と iPhone/macOS の互換性を維持する設定
   fruit:encoding = native
   fruit:metadata = stream
   fruit:resource = file
   fruit:nfs_aces = no
   fruit:aapl = no

   # iPhone（iOS）での動作向け
   ea support = yes
   streams_xattr:prefix = user.

   # Windows でのファイル名トラブル防止
   mangled names = yes
   case sensitive = no

   # lost+found非表示
   veto files = /lost+found/
   hide files = /lost+found/
   hide dot files = yes
```
Samba再起動
```
sudo systemctl restart smbd
```
Sambaパスワード設定
```
sudo smbpasswd -a pi
```

### Tailscale
事前にTailscaleアカウントを作成
```
curl -fsSL https://tailscale.com/install.sh | sh
```
以下のコマンド実行後、URLにアクセスしてログインする
```
sudo tailscale up --accept-dns=true
```
IPの確認
```
tailscale ip -4
```

## Edit
<code>flask_file_browser</code>以下のファイルを一部編集
***
### <code>env.env</code>の編集
記載例
<pre>
   SSD_UUID=***********************
   SHARED_FOLDER=/home/pi/***
   VENV_PATH=/home/pi/flask_file_browser/venv
   SYNC_DB_AND_THUMBNAILS=/home/pi/flask_file_browser/sync_db_and_thumbnails.py
   PORT=7001
</pre>

### <code>templates/index.html</code>の編集
<pre>
   # line9 fontawesome kitのscript URL
   <script src="" crossorigin="anonymous"></script>
</pre>

## Pre-check
<code>flask_file_browser</code>内で以下を実行
```
source venv/bin/activate
```
```
python3 app.py
```
動作確認を行う

## systemd
サービス化して自動起動を有効にする
```
cd /usr/lib/systemd/system
```
```
sudo nano flask_file_browser.service
```
以下を記述
```
[Unit]
Description=Flask File Browser Service
After=network.target

[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/flask_file_browser　#適宜変更
ExecStart=/home/pi/flask_file_browser/venv/bin/gunicorn -w 4 -b 0.0.0.0:7001 app:app #venvの位置とポート番号
Restart=always

[Install]
WantedBy=multi-user.target
```
サービスを起動
```
sudo systemctl start flask_file_browser
```
```
sudo systemctl enable flask_file_browser
```

## Access
TailscaleのコンソールでMachine名を確認する(HOST名)
<br />
例: Machine名:<code>pi5</code>, Sambaの共有名<code>Pi5</code>の場合

* URL
```
http://pi5:7001/
```
* Windowsエクスプローラー
```
\\pi5\Pi5
```

## Completion
![Image](https://github.com/user-attachments/assets/95b688a7-14d9-4574-bf9d-f2371c2d4252)
![Image](https://github.com/user-attachments/assets/15710d96-689a-4afd-81a8-5b0a48557327)
![Image](https://github.com/user-attachments/assets/006ede7a-d834-4ae6-b5dc-675caa9bf7a8)
![Image](https://github.com/user-attachments/assets/7c173faf-c25d-434e-aa76-902a2691bfc3)
![Image](https://github.com/user-attachments/assets/17d299e0-d4f0-481f-ace1-c2e88c2601ca)
![Image](https://github.com/user-attachments/assets/1e473489-3ab5-4ba7-bc6f-c4901ba9370e)

## ライセンス
MIT License © 2025 py-raspi  
詳細は [LICENSE](LICENSE) を参照してください。
