# 入門！生成 AI を使った検索システム

## はじめに

本ハンズオンでは、生成 AI を用いた検索システムを、Vertex AI Search で構築します。チュートリアルに記載された内容を元に進めていきますので、こちらの画面の内容をよく読みながらコマンドの入力や、画面上の操作を進めてください。

ハンズオンの説明は [GitHub 上のページ](https://github.com/shonuma/vertex-ai-search-hands-on-202505/blob/main/tutorial.md) のページからでも参照が可能です。

設定画面のキャプチャを確認したい場合は[ラボ](https://explore.qwiklabs.com/classrooms/17237/labs/99713)のページからご確認いただけます。 

準備ができたら、**開始** ボタンを押してください。

## ハンズオン前半

ハンズオンの前半では、今回の検索システムで利用する検索エンジンを作成していきます。

具体的には、以下の作業を進めていきます。
- API の有効化
- Cloud Storage バケットの作成
- 検索対象データの取得
- 検索対象データのベクトル化
- 検索エンジンアプリの作成

準備ができたら、**次へ** ボタンを押してください。

この画面の説明は読み返すことができます。読み返したい場合は **前へ** ボタンを押してください。

## 環境変数の設定 (Cloud Shell が再起動してしまった場合も実施をお願いします)

環境変数 `GOOGLE_CLOUD_PROJECT` に GCP プロジェクト ID を設定します。
- 現在の Google Cloud プロジェクト ID は <walkthrough-project-id/> です。

```bash
export GOOGLE_CLOUD_PROJECT="<walkthrough-project-id/>"
gcloud config set project $GOOGLE_CLOUD_PROJECT
```

以下のコマンドを実行することで、正しく設定できていることを確認できます。
```bash
echo $GOOGLE_CLOUD_PROJECT
```
 `<walkthrough-project-id/>` が出力されれば成功です。

`gcloud` コマンドのデフォルトプロジェクトの設定
```bash
gcloud config list project | grep project
```
`project = <walkthrough-project-id/>` と表示されていれば成功です。

回線の切断や、長時間の離席により Cloud Shell との接続が切断されてしまう場合があります。本コマンドを再実行することで、必要な環境変数を再設定できます。

## API の有効化
Google Cloud では、利用したい機能ごとに API の有効化を行う必要があります。ここでは、以降のハンズオンで利用する機能を事前に有効化しておきます。

今回のハンズオンでは以下のサービスを利用しますので、該当の API を有効化します。
- Cloud Run
- Vertex AI
- Vertex AI Search
- Cloud Storage
- Firestore

以下のコマンドを実行します。

```bash
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  discoveryengine.googleapis.com
```

`Operation ... finished successfully.` と表示されたら成功です。

## 事例 PDF データを設置する Cloud Storage バケットの作成

事例 PDF データを設置するためのオブジェクト ストレージを作成しましょう。

`<walkthrough-project-id/>-search-handson` という名称の `Cloud Storage` バケットを、東京リージョン（`asia-northeast1`）に作成します。

以下のコマンドを実行します。

```bash
gcloud storage buckets create gs://${GOOGLE_CLOUD_PROJECT}-search-handson --location=asia-northeast1 --project ${GOOGLE_CLOUD_PROJECT}
```

以下のコマンドを実行して何も表示されなければ作成に成功しています。
```bash
gcloud storage ls gs://${GOOGLE_CLOUD_PROJECT}-search-handson
```

上記の方法のほか、以下の方法でも Cloud Storage のバケットが作成されたことを確認できます。
1. 画面上部の検索バーに **Storage** と入力します。
2. 検索候補から **Cloud Storage** を選択します。
3. 画面左部のメニューから **バケット** を選択します。
4. `<walkthrough-project-id/>-search-handson` というバケットが一覧に表示されていることを確認します。

## 事例 PDF データのコピー

作成した Cloud Storage バケットに、事例 PDF データをコピーします。事例 PDF データは 165 件あります。

以下のコマンドを実行します。

```bash
gcloud storage cp -r gs://dev-genai-handson-25q2-static/pdfs gs://${GOOGLE_CLOUD_PROJECT}-search-handson/
```

コマンドが終了したら、コピーが完了しています。

以下のコマンドを実行して、`<walkthrough-project-id/>-search-handson/pdfs/` と表示されればOKです。

```bash
gcloud storage ls gs://${GOOGLE_CLOUD_PROJECT}-search-handson/
```

データが 165 件あることは、以下のコマンドで確認できます。

```bash
gcloud storage ls gs://${GOOGLE_CLOUD_PROJECT}-search-handson/pdfs/*.pdf | wc -l
```

これでデータの準備ができました。

続いて、検索エンジンを作成していきましょう。

## 検索エンジンの作成

本手順では、先程準備した事例 PDF データを検索するための検索エンジンを作成します。

検索エンジンを作成するには、**検索対象のデータの作成（ベクトル化）** を行い、ベクトル化したデータを**検索するための機能** を設定します。

## AI Applications を開く

上部の検索バーに `AI applications` と入力し、**AI applications** を選択して開きます。

[このような画面](https://storage.googleapis.com/dev-genai-handson-25q2-static/images/enable_api_ai_applications)が表示された場合は、赤枠内のボタンを押して、サービスの利用に必要な API の有効化を実施してください。

## データストアの作成

まずは、検索対象のデータのベクトル化を行っていきましょう。
本手順の画面キャプチャは、Qwiklab のページに記載がありますのでそちらも参考にしてください。

1. 画面左部メニューの **データストア** を選択し、画面上部の **データストアを作成** を選択します。
2. データソースを選択する画面が表示されるので、`Cloud Storage` を選択します。
3. Cloud Storage のデータのインポート設定が表示されます、今回は PDF データを利用するので、`非構造化ドキュメント` を選択します。同期の頻度は `1 回限り` に設定します。
4. インポートするフォルダまたはファイルを指定します。先ほど作成した Cloud Storage バケット名（`<walkthrough-project-id/>-search-handson`）を指定します。または、**参照** から、バケットの一覧から選択していただいても大丈夫です。
5. **続行** を押します。
6. 名称、及びデータのローケーションを設定します。ロケーションは `global` を選択し、データストア名を `genai-handson-2025-gcs` に指定します。
7. **作成** を押します。

以上で、データストアの作成（ベクトル化）は完了です。

データストアの作成には 数分 〜 10 分程度の時間がかかります。

## 検索エンジンの作成

続いて、検索エンジンを作成していきます。
本手順の画面キャプチャは、Qwiklab のページに記載がありますのでそちらも参考にしてください。

1. 画面左部メニューの **アプリ** を選択し、画面上部の **アプリを作成する** を選択します。
2. アプリの種類で、**カスタム検索** の **作成** ボタンをクリックします。
3. アプリの構成の検索で、**Enterprise エディションの機能、高度な LLM 検索** を有効化します（チェックされていればそのままでOKです）。
4. アプリ名を `genai-handson-2025-app` に設定します。
5. 会社名または組織名には `Google Cloud` と入力します。
6. アプリのロケーションは `global` のままで **続行** を押します。
7. データストアの選択画面が表示されます。先ほどの手順で作成した `genai-handson-2025-gcs` を指定します。
8. **作成** を押します。

アプリが正常に作成されました、とポップアップが表示されたら成功です。

アプリの作成が完了し動作し始めるには、数分 〜 5 分程度の時間がかかります。

## 検索のプレビュー画面

アプリの **プレビュー** をクリックします。検索ウィンドウが表示されるので、適当な検索ワードを入力して検索を行ってみます。

アプリの準備ができていない場合 `検索プレビューの準備がまだできていません` とエラーが表示されます。しばらく待ってから、再度検索をお試しください。

一定時間経過すると、検索結果の要約及び検索結果が表示されるようになります。

## ハンズオン前半の完了

前半は以上で終了です。お疲れ様でした！

## ハンズオン後半に入る前に…

環境変数、及び `gcloud` コマンドにプロジェクト ID を再設定をしておきましょう。

```bash
export GOOGLE_CLOUD_PROJECT="<walkthrough-project-id/>"
gcloud config set project $GOOGLE_CLOUD_PROJECT
```

## ハンズオン後半

ハンズオンの後半では、さきほど作成した検索システムをアプリケーションに組み込み、コンテナ化して Cloud Run にデプロイを行います。

具体的には、以下の作業を進めていきます。
- Cloud Run へのアプリケーションデプロイのための準備
- Cloud Run へのアプリケーションのデプロイ
- Cloud Run アプリの動作確認
- 検索履歴保存機能の追加

## Cloud Run デプロイ用のサービスアカウントの作成

Cloud Run へデプロイを行うためのサービスアカウントを作成します。

```bash
gcloud iam service-accounts create ai-agent-bootcamp-2025-sa --display-name "Service Account for Cloud Run Service" --project <walkthrough-project-id/>
```

`Created service account ai-agent-bootcamp-2025-sa` と表示されれば成功です。

続いて、必要な権限を付与していきます。

```bash
for role in roles/artifactregistry.writer roles/datastore.user roles/storage.objectUser roles/discoveryengine.user roles/aiplatform.user roles/run.admin;do gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} --member='serviceAccount:ai-agent-bootcamp-2025-sa@<walkthrough-project-id/>.iam.gserviceaccount.com' --role=${role}; done;
```

これで、サービスアカウントの準備ができました。

## 検索エンジンの ID を取得

アプリケーションから実行する検索エンジンの ID を取得します。

1. 上部の検索バーに `AI applications` と入力し、**AI applications** を選択して開きます。
2. 画面左部メニューの **アプリ** を選択します。
3. 画面右部に表示されているアプリの `genai-handson-2025` の情報の **ID** にかかれている文字列を控えておきます。これが検索エンジンの ID となり、通常は `genai-handson-2025-xxxx_yyyy` のような形式の文字列です。
4. 以下のコマンドを実行して、検索エンジンのIDを環境変数に設定します。

```bash
export ENGINE_ID=<検索エンジンのID>
```

## Cloud Run へのデプロイ

Cloud Run へのデプロイを実施します。以下のコマンドを実行することで、ソースコードを Cloud Run へデプロイすることができます。

まずは、リポジトリ直下のディレクトリへ移動します。

```bash
cd ~/vertex-ai-search-hands-on-202505
```

続いて、デプロイコマンドを実行しましょう。

- `source` には、ソースコードのパスを指定します。
- `set-env-vars` で、アプリの実行に必要な環境変数を設定しています。
- `--service-account` には、Cloud Run サービス上で API の実行を行うサービスアカウントを指定します。
- `build-service-account` には、デプロイ作業を実行するサービスアカウントを指定します。
- `allow-unauthenticated` を指定すると、認証なしにサービスへアクセスすることが可能になります。
- `region` は、デプロイするリージョンを指定します。

```bash
gcloud run deploy --set-env-vars PROJECT_ID=${GOOGLE_CLOUD_PROJECT},LOCATION=global,ENGINE_ID=${ENGINE_ID},FIRESTORE_COLLECTION_NAME=vais-queries ai-agent-bootcamp-2025-service --source handson/ --service-account=ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --build-service-account=projects/${GOOGLE_CLOUD_PROJECT}/serviceAccounts/ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --allow-unauthenticated --region asia-northeast1
```

デプロイ時に Artifact Registry の Repositry を作成するか聞かれますので、 `y` と入力します。
```
Deploying from source requires an Artifact Registry Docker repository to store built containers. A repository named [cloud-run-source-deploy] in region [asia-northeast1] will be 
created.
```

デプロイに成功すると以下のようなメッセージが表示されます。`.app` で終わる URL にアクセスして、検索アプリケーションが動作していることを確認しましょう。
```
Service [ai-agent-bootcamp-2025-service] revision [...] has been deployed and is serving 100 percent of traffic.
Service URL: <URL>
```

## デプロイされたサービスの動作確認

テキストエリアに検索クエリを入力して、検索を試してみてください。
検索結果と、検索結果の要約が表示されていることを確認しましょう。


## 検索履歴機能の実装

本アプリに、検索履歴を保存する機能を追加してみましょう。

## 再デプロイ


## ハンズオン後半の完了

ハンズオンは以上で終了です。お疲れ様でした！