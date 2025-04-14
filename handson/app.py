# -*- coding: utf-8 -*-
import gradio as gr
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core import exceptions
import os
from urllib.parse import quote # URLエンコード用

# --- 環境変数 (変更なし) ---
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION")
DATA_STORE_ID = os.environ.get("DATA_STORE_ID")
# ----------------------------------------------------------

# --- Vertex AI Search 設定 (変更なし) ---
serving_config = (
    f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/"
    f"dataStores/{DATA_STORE_ID}/servingConfigs/default_config"
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

# --- 検索関数 (変更なし) ---
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

        return output_md

    except exceptions.GoogleAPICallError as e:
        print(f"API Error: {e}")
        error_message = f"検索中にAPIエラーが発生しました: {e.message}\n"
        if e.status_code == 403:
            error_message += "権限不足の可能性があります。Vertex AI APIの有効化やサービスアカウントのロールを確認してください。"
        elif e.status_code == 404:
            error_message += f"データストアが見つからない可能性があります。設定値 ({PROJECT_ID}, {LOCATION}, {DATA_STORE_ID}) を確認してください。"
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

    gr.Examples(
        examples=[
            ["Gemini を活用した事例"],
            ["BigQuery の事例"],
            ["ゲーム業界での生成 AI を活用した事例"]
        ],
        inputs=query_input,
        label="入力例"
    )

    with gr.Row():
        clear_button = gr.Button("クリア")
        submit_button = gr.Button("検索", variant="primary")

    results_output = gr.Markdown(label="検索結果")

    # --- ボタンのアクション (変更なし) ---
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

# --- アプリケーションの起動 (変更なし) ---
if __name__ == "__main__":
    server_port = int(os.environ.get('PORT', 8080))
    print(f"\nGradio アプリをポート {server_port} で起動します...")
    demo.launch(server_name="0.0.0.0", server_port=server_port)
