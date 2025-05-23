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

`gcloud` コマンドのデフォルトプロジェクトも確認しておきます。
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

## 必要な権限の付与

ログインしているメールアドレスをコピーして、`USER_ID` という環境変数に設定します。
[コンソールの右上のアイコンをクリック](https://storage.googleapis.com/dev-genai-handson-25q2-static/images/user_name_1)するか、[ラボの開始画面](https://storage.googleapis.com/dev-genai-handson-25q2-static/images/user_name_2)から確認できます。


```bash
export USER_ID=<user id>
```

以下のコマンドで、ユーザー ID が出力されていれば成功です。
```bash
echo $USER_ID
```

上記を設定した後、以下のコマンドを実行して `Cloud Storage` にアクセスするための権限 (`roles/storage.objectUser`) を付与します。

```bash
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} --member "user:${USER_ID}" --role=roles/storage.objectUser
```

これで、検索エンジン作成に必要な権限の付与は完了です。

## AI Applications を開く

これから、検索エンジンの作成手順に入っていきます。

上部の検索バーに `AI applications` と入力し、**AI applications** を選択して開きます。

[このような画面](https://storage.googleapis.com/dev-genai-handson-25q2-static/images/enable_api_ai_applications)が表示されるので、赤枠内のボタンを押してサービスの利用に必要な API の有効化を実施してください。

## データストアの作成

まずは、検索対象のデータのベクトル化を行っていきましょう。
本手順の画面キャプチャは、ラボのページに記載がありますのでそちらも参考にしてください。

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
本手順の画面キャプチャは、ラボのページに記載がありますのでそちらも参考にしてください。


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
- 要約のカスタマイズ

## Cloud Run デプロイ用のサービスアカウントの作成

Cloud Run へデプロイを行うためのサービスアカウントを作成します。

```bash
gcloud iam service-accounts create ai-agent-bootcamp-2025-sa --display-name "Service Account for Cloud Run Service" --project <walkthrough-project-id/>
```

`Created service account ai-agent-bootcamp-2025-sa` と表示されれば成功です。

続いて、必要な権限を付与していきます。

```bash
for role in roles/artifactregistry.writer roles/datastore.user roles/storage.objectUser roles/discoveryengine.user roles/aiplatform.user roles/run.admin roles/logging.logWriter;do gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} --member='serviceAccount:ai-agent-bootcamp-2025-sa@<walkthrough-project-id/>.iam.gserviceaccount.com' --role=${role}; done;
```

これで、サービスアカウントの準備ができました。

## 検索エンジンの ID を取得

アプリケーションから実行する検索エンジンの ID を取得します。

1. 上部の検索バーに `AI applications` と入力し、**AI applications** を選択して開きます。
2. 画面左部メニューの **アプリ** を選択します。
3. 画面右部に表示されているアプリの `genai-handson-2025` の情報の **ID** にかかれている文字列を控えておきます。これが検索エンジンの ID となり、通常は `genai-handson-2025-app_xxxxxx` のような形式の文字列です。
4. 以下のコマンドを実行して、検索エンジンのIDを環境変数に設定します。`<search engine id>` には、上記で取得した ID を指定してください。

```bash
export ENGINE_ID=<search engine id>
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
- `service-account` には、Cloud Run サービス上で API の実行を行うサービスアカウントを指定します。
- `build-service-account` には、デプロイ作業を実行するサービスアカウントを指定します。
- `allow-unauthenticated` を指定すると、認証なしにサービスへアクセスすることが可能になります。
- `region` は、デプロイするリージョンを指定します。

```bash
gcloud run deploy --set-env-vars PROJECT_ID=${GOOGLE_CLOUD_PROJECT},LOCATION=global,ENGINE_ID=${ENGINE_ID},FIRESTORE_COLLECTION_NAME=vais-queries ai-agent-bootcamp-2025-service --source handson/ --service-account=ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --build-service-account=projects/${GOOGLE_CLOUD_PROJECT}/serviceAccounts/ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --allow-unauthenticated --region asia-northeast1
```

デプロイ時に Artifact Registry の Repositry を作成するか聞かれますので、 `y` と入力します。


```
# 出力例のため実行不要
Deploying from source requires an Artifact Registry Docker repository to store built containers. A repository named [cloud-run-source-deploy] in region [asia-northeast1] will be 
created.
```

デプロイに成功すると以下のようなメッセージが表示されます。`.app` で終わる URL にアクセスして、検索アプリケーションが動作していることを確認しましょう。

```
# 出力例のため実行不要
Service [ai-agent-bootcamp-2025-service] revision [...] has been deployed and is serving 100 percent of traffic.
Service URL: <URL>
```

## デプロイされたサービスの動作確認

テキストエリアに検索クエリを入力して、検索を試してみてください。
検索結果と、検索結果の要約が表示されていることを確認しましょう。

[トップページの表示例](https://storage.googleapis.com/dev-genai-handson-25q2-static/images/app_top_page)

[検索ボタンを押したときの動作例](https://storage.googleapis.com/dev-genai-handson-25q2-static/images/app_search_result)

以上でデプロイは完了です。

## 検索履歴機能の実装

本アプリに、検索履歴を保存する機能を追加してみましょう。

検索履歴の保持には、ドキュメント 指向 データベースである `Firestore` を利用します。

## Firestore データベースの作成

まずは、検索履歴を保持するための Firestore データベースを作成します。以下のコマンドを実行します。

```bash
gcloud firestore databases create --database="(default)" --location="asia-northeast1" --type=firestore-native
```

以下のコマンドを実行し、 `name: projects/<walkthrough-project-id/>/databases/(default)` と表示されることを確認しましょう。

```bash
gcloud firestore databases list | grep '(default)'
```

## Firestore データベースへ接続するための変更を実施

続けて、ソースコードを変更します。作業ディレクトリに移動します。

```bash
cd ~/vertex-ai-search-hands-on-202505
```

以下のコマンドを実行して、デフォルトの検索候補を返す関数 `set_dataset_default_examples` を `update_dataset_examples` に置き換えます。

```bash
sed -i 's/fn=set_dataset_default_examples/fn=update_dataset_examples/' handson/app.py
```

ソースコードの変更がうまくできたかどうかは、以下のコマンドで確認可能です。

```bash
git diff
```

以下のように、差分が表示されたら成功です。

```diff
# 出力例のため実行不要です
diff --git a/handson/app.py b/handson/app.py
index 538b8b5..af2a917 100644
--- a/handson/app.py
+++ b/handson/app.py
@@ -311,7 +311,7 @@ with gr.Blocks(css="style.css", title="AI Agent Bootcamp 検索アプリハン
     demo.load(
         # set_dataset_default_examples: default
         # update_dataset_examples: get/set from firestoer
-        fn=set_dataset_default_examples,
+        fn=update_dataset_examples,
         inputs=None,
         outputs=dataset_component 
     )
```

## デプロイと動作確認

上記が完了したら、再デプロイを行ってみましょう。

```bash
gcloud run deploy --set-env-vars PROJECT_ID=${GOOGLE_CLOUD_PROJECT},LOCATION=global,ENGINE_ID=${ENGINE_ID},FIRESTORE_COLLECTION_NAME=vais-queries ai-agent-bootcamp-2025-service --source handson/ --service-account=ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --build-service-account=projects/${GOOGLE_CLOUD_PROJECT}/serviceAccounts/ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --allow-unauthenticated --region asia-northeast1
```

デプロイが完了したら動作確認をしてみましょう。

適当な文字列で検索を実行したあと、入力例の欄にに検索履歴が表示されていればOKです。

**入力例** に検索履歴が表示されていることが確認できれば OK です。

[検索履歴の表示例](https://storage.googleapis.com/dev-genai-handson-25q2-static/images/query_history)

## 要約のカスタマイズ

最後に、生成 AI で作成している検索結果の要約をカスタマイズしてみましょう。

検索エンジンの API のパラメータにシステム指示を入力するように変更していきます。

## 要約のカスタマイズを行うための変更を実施

作業ディレクトリに移動します。

```bash
cd ~/vertex-ai-search-hands-on-202505
```

以下のコマンドを実行して、システム指示を入力できるパラメータ `preamble` に指示を入力します。
※ 本コマンドはマルチバイト文字列を含むため、クリップボードにコピーしてからの貼り付けをお願いします。

```bash
sed -ie 's/preamble=\".*\"/preamble="小学生でも理解できる表現で説明してください"/' handson/app.py
```

## デプロイと動作確認

上記が完了したら、再デプロイを行ってみましょう。

```bash
gcloud run deploy --set-env-vars PROJECT_ID=${GOOGLE_CLOUD_PROJECT},LOCATION=global,ENGINE_ID=${ENGINE_ID},FIRESTORE_COLLECTION_NAME=vais-queries ai-agent-bootcamp-2025-service --source handson/ --service-account=ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --build-service-account=projects/${GOOGLE_CLOUD_PROJECT}/serviceAccounts/ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --allow-unauthenticated --region asia-northeast1
```

デプロイが完了したら動作確認をしてみましょう。

適当な文字列で検索を実行し、表示される要約（概要）に、システム指示が反映されていればOKです。

## 他のシステム指示も試してみる

時間があれば、他の指示も試してみましょう。

以下のコマンドを実行すると、**関西弁風**に説明を行ってくれるようになります。

※ 本コマンドはマルチバイト文字列を含むため、クリップボードにコピーしてからの貼り付けをお願いします。
```bash
sed -ie 's/preamble=\".*\"/preamble="関西弁で説明してください"/' handson/app.py
```

そのほか、以下のような指示も試してみましょう。`関西弁で説明してください` の部分を書き換えてコマンドを実行します。
- 100 文字程度で説明してください
- 男性と女性の会話形式で説明してください

デプロイを行い、動作確認を行ってみましょう。システム指示の表現が変化していることを確認できれば OK です。

```bash
gcloud run deploy --set-env-vars PROJECT_ID=${GOOGLE_CLOUD_PROJECT},LOCATION=global,ENGINE_ID=${ENGINE_ID},FIRESTORE_COLLECTION_NAME=vais-queries ai-agent-bootcamp-2025-service --source handson/ --service-account=ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --build-service-account=projects/${GOOGLE_CLOUD_PROJECT}/serviceAccounts/ai-agent-bootcamp-2025-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com --allow-unauthenticated --region asia-northeast1
```

## ログを確認してみる

本システムでは、検索実行時にログを `Cloud Logging` というログ集積サービスに出力しています。そのログを確認してみましょう。

1. 画面上部の検索バーに **Logging** と入力します。
2. ログエクスプローラに以下の情報を入力し、**クエリを実行**を押します。

```bash
severity=INFO
logName=projects/<walkthrough-project-id/>/logs/gradio_vertex_ai_search_app
```

3. 以下のような検索クエリが含まれるログが表示されていることを確認します。

```bash
# 出力例のため実行不要です
Logged new query: 'ゲームの事例'
Search successful for query: 'ゲームの事例'. Results returned.
Fetched 3 recent queries from Firestore for Dataset update.
```

[結果表示例](https://storage.googleapis.com/dev-genai-handson-25q2-static/images/cloud_logging_query)

以上で、ログの出力が確認できました。

## Congratulations! (ハンズオンの完了)

ハンズオンは以上で終了です。お疲れ様でした！

画面右上部の **✕ボタン** を押して、チュートリアルを閉じることができます。

本環境は Google Cloud で用意された環境のため、シークレットウィンドウをそのまま閉じていただいて OK です。タイマー終了時までは、本環境を自由にお触りいただけます。