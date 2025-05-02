# -*- coding: utf-8 -*-
import gradio as gr
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core import exceptions
import os
from urllib.parse import quote # URLエンコード用
from google.cloud import firestore

# --- 環境変数 ---
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION")
ENGINE_ID = os.environ.get("ENGINE_ID")
FIRESTORE_COLLECTION_NAME = os.environ.get("FIRESTORE_COLLECTION_NAME")
# ----------------------------------------------------------

# --- Vertex AI Search 設定 ---
serving_config = (
    f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/"
    f"engines/{ENGINE_ID}/servingConfigs/default_serving_config"
)

client = None
initialization_error_message = None
try:
    client = discoveryengine.SearchServiceClient()
except Exception as e:
    initialization_error_message = (
        f"エラー: Vertex AI Search クライアントの初期化に失敗しました。\n{e}\n\n"
        "認証情報 (gcloud auth application-default login) やライブラリが正しく設定されているか確認してください。"
    )
    print(initialization_error_message)

# Firestore クライアントの初期化
try:
    db = firestore.Client(project=PROJECT_ID) # プロジェクトIDを明示的に指定
    print(f"Firestore client initialized successfully for project {PROJECT_ID}.")
except Exception as e:
    print(f"Failed to initialize Firestore client: {e}")
    db = None

# --- Firestore から直近の検索クエリを取得する関数 ---
default_examples_list_for_dataset = [ # デフォルトの検索例をグローバルで定義
    ["Gemini を活用した事例"],
    ["BigQuery の事例"],
    ["ゲーム業界での生成 AI を活用した事例"]
]

def update_dataset_examples(limit=3):
    """
    Firestore から直近の検索クエリを取得し、gr.Dataset を更新するための情報を返す。
    取得できない場合やデータがない場合はデフォルトのリストを使用する。
    """
    if not db:
        print("Firestore client not initialized. Returning default examples for Dataset.")
        return gr.update(samples=default_examples_list_for_dataset)

    recent_queries_for_dataset = []
    try:
        query_log_ref = db.collection(FIRESTORE_COLLECTION_NAME)\
                          .order_by("updatedAt", direction=firestore.Query.DESCENDING)\
                          .limit(limit)
        docs = query_log_ref.stream()
        for doc_snapshot in docs:
            data = doc_snapshot.to_dict()
            if "query" in data:
                recent_queries_for_dataset.append([data["query"]])

        if recent_queries_for_dataset:
            print(f"Fetched {len(recent_queries_for_dataset)} recent queries from Firestore for Dataset update.")
            return gr.update(samples=recent_queries_for_dataset)
        else:
            print("No recent queries found in Firestore. Returning default examples for Dataset update.")
            return gr.update(samples=default_examples_list_for_dataset)
    except Exception as e:
        print(f"Error fetching recent queries from Firestore for Dataset update: {e}. Returning default examples.")
        return gr.update(samples=default_examples_list_for_dataset)

# --- 検索関数 ---
def search_vertex_ai(query: str) -> str:
    """Vertex AI Search を使用して検索を実行し、結果を Markdown 形式で返す関数"""
    global client, initialization_error_message

    if initialization_error_message:
        return initialization_error_message

    if not client:
        return "エラー: Vertex AI Search クライアントが利用できません。アプリケーションを再起動してください。"

    if not query:
        return "検索クエリを入力してください。"

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=5,
        content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True,
                max_snippet_count=1
            ),
            summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=3,
                include_citations=True
            ),
        )
    )

    try:
        response = client.search(request=request)
        output_md = ""

        if response.summary and response.summary.summary_text:
            output_md += f"## 概要:\n{response.summary.summary_text}\n\n---\n\n"

        output_md += "## 検索結果:\n"
        if not response.results:
            output_md += "関連する結果は見つかりませんでした。"
            return output_md

        for i, result in enumerate(response.results):
            doc = result.document
            title = doc.derived_struct_data.get('title', 'タイトルなし')
            link = doc.derived_struct_data.get('link', '')

            if link and link.startswith("gs://"):
                link = link.replace("gs://", "https://storage.cloud.google.com/", 1)

            encoded_link = quote(link, safe='/:?=&#') if link else ''
            snippet = ""
            if 'snippets' in doc.derived_struct_data and doc.derived_struct_data['snippets']:
                snippet = doc.derived_struct_data['snippets'][0].get('snippet', '')

            if encoded_link:
                output_md += f"### {i+1}. [{title}]({encoded_link})\n"
            else:
                output_md += f"### {i+1}. {title}\n"

            if snippet:
                snippet_md = snippet.replace("<em>", "*").replace("</em>", "*")
                output_md += f"**スニペット:** {snippet_md}\n"
            output_md += "\n"

        # --- Firestore に検索クエリをログとして保存または更新 ---
        if db: # Firestore クライアントが初期化されていれば実行
            try:
                # まず、同じクエリが既に存在するか確認
                query_ref = db.collection(FIRESTORE_COLLECTION_NAME).where("query", "==", query).limit(1)
                docs = list(query_ref.stream()) # クエリ結果を取得

                if docs: # ドキュメントが存在する場合 (重複クエリ)
                    doc_snapshot = docs[0] # 最初のドキュメントを取得 (limit(1)なので最大1件)
                    doc_ref = doc_snapshot.reference
                    # count をインクリメントし、updatedAt を更新
                    doc_ref.update({
                        "count": firestore.Increment(1),
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                    })
                else: # ドキュメントが存在しない場合 (新規クエリ)
                    doc_ref = db.collection(FIRESTORE_COLLECTION_NAME).document() # 新しいドキュメントIDを自動生成
                    doc_ref.set({
                        "query": query,
                        "createdAt": firestore.SERVER_TIMESTAMP, # 作成日時
                        "updatedAt": firestore.SERVER_TIMESTAMP, # 更新日時 (作成時も設定)
                        "count": 1, # 初期カウント
                    })
            except Exception as e:
                print(f"Error logging or updating query in Firestore: {e}")
                # Firestoreへのロギングエラーは検索処理自体を妨げないようにする
        else:
            print("Firestore client not initialized. Skipping query logging.")

        return output_md

    except exceptions.GoogleAPICallError as e:
        print(f"API Error: {e}")
        error_message = f"検索中にAPIエラーが発生しました: {e.message}\n"
        if e.status_code == 403:
            error_message += "権限不足の可能性があります。Vertex AI APIの有効化やサービスアカウントのロールを確認してください。"
        elif e.status_code == 404:
            error_message += f"検索エンジンが見つからない可能性があります。設定値 ({PROJECT_ID}, {LOCATION}, {ENGINE_ID}) を確認してください。"
        else:
             error_message += "リクエスト内容や設定を確認してください。"
        return error_message
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        return f"予期せぬエラーが発生しました: {e}"

# --- Gradio UI ---
# cssパラメータで外部CSSファイルを指定
with gr.Blocks(css="style.css", title="AI Agent Bootcamp 検索アプリハンズオン") as demo:
    gr.Markdown(
        """
        # AI Agent Bootcamp 検索アプリハンズオン
        検索クエリを入力し、「検索」ボタンを押してください。
        """
    )

    query_input = gr.Textbox(
        label="検索クエリ",
        placeholder="検索したいキーワードを入力...",
        info="Vertex AI Search Engine に問い合わせます。",
        elem_id="search-input-box" # IDはCSSファイル内で使用するため残す
    )

    dataset_component = gr.Dataset(
        components=[query_input], # このデータセットの各行がどの入力コンポーネントに対応するか
        samples=default_examples_list_for_dataset, # 初期表示はデフォルト
        label="入力例 (クリックで入力)",
        # type="values", # Gradioのバージョンによっては不要
        # headers=["検索クエリ例"] # 必要に応じてヘッダーを設定
    )

    with gr.Row():
        clear_button = gr.Button("クリア")
        submit_button = gr.Button("検索", variant="primary")

    results_output = gr.Markdown(label="検索結果")

    # --- ボタンのアクション ---
    submit_button.click(
        fn=search_vertex_ai,
        inputs=query_input,
        outputs=results_output
    )
    clear_button.click(
        lambda: ("", ""),
        inputs=None,
        outputs=[query_input, results_output]
    )

    # Dataset の行が選択されたときの処理
    def handle_dataset_select(evt: gr.SelectData):
        if evt.value: # evt.value は選択された行のデータ (例: ["選択されたクエリ"])
            selected_query = evt.value[0] # 最初の要素（クエリ文字列）を取得
            return gr.update(value=selected_query)
        return gr.update() # 何も選択されていない、または値がない場合は更新しない

    dataset_component.select(
        fn=handle_dataset_select,
        inputs=None,
        outputs=query_input # query_input テキストボックスを更新
    )

    # ページロード時に Examples を更新する
    demo.load(
        fn=update_dataset_examples, # Firestoreから取得し、gr.update()を返す関数
        inputs=None, # この関数への入力はなし
        outputs=dataset_component # 更新対象のDatasetコンポーネント
    )

# --- アプリケーションの起動 ---
if __name__ == "__main__":
    server_port = int(os.environ.get('PORT', 8080))
    demo.launch(server_name="0.0.0.0", server_port=server_port)
