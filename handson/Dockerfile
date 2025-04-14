# ベースイメージとして Python 3.10 のスリム版を使用
FROM python:3.10-slim

# 環境変数設定
# Pythonの出力をバッファリングしないように設定 (ログがすぐに見えるように)
ENV PYTHONUNBUFFERED True
# Cloud Runが提供するポート番号 (標準の8080をデフォルトに設定)
ENV PORT 8080


# 作業ディレクトリを作成し、設定
WORKDIR /app

# 必要なライブラリを記述した requirements.txt をコピー
COPY requirements.txt requirements.txt

# pipをアップグレードし、requirements.txt に基づいてライブラリをインストール
# --no-cache-dir オプションでキャッシュを使用せず、イメージサイズを削減
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコードを作業ディレクトリにコピー
COPY app.py .
COPY style.css .

# コンテナがリッスンするポートを公開 (Cloud Runの標準デフォルト 8080)
EXPOSE 8080

# コンテナ起動時に実行するコマンド
# app.py 内で環境変数 PORT を参照して Gradio サーバーを起動
CMD ["python", "app.py"] 


