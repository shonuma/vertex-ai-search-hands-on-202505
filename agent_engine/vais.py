from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core import exceptions
import os
from urllib.parse import quote 

# --- 環境変数 ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("LOCATION", "global")
ENGINE_ID = os.environ.get("ENGINE_ID")
# ----------------------------------------------------------


# --- Vertex AI Search 設定 ---
serving_config = (
    f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/"
    f"engines/{ENGINE_ID}/servingConfigs/default_serving_config"
)

client = discoveryengine.SearchServiceClient()

# --- 検索関数 ---
def search_vertex_ai(
        query: str
    ) -> str:
    """Vertex AI Search を使用して検索を実行し、結果を Markdown 形式で返す関数"""

    global client, serving_config

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
                include_citations=True,
                model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                    # set preamble
                    # - 小学生でも理解できる表現で説明してください
                    preamble=""
                ),
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
                output_md += f"{snippet_md}\n"
            output_md += "\n"

        return output_md

    except exceptions.GoogleAPICallError as e:
        error_message_detail = f"API Error during search for query '{query}': {e}"

        error_message = f"検索中にAPIエラーが発生しました: {e.message}\n"
        if e.status_code == 403:
            error_message += "権限不足の可能性があります。Vertex AI APIの有効化やサービスアカウントのロールを確認してください。"
        elif e.status_code == 404:
            error_message += f"検索エンジンが見つからない可能性があります。設定値 ({PROJECT_ID}, {LOCATION}, {ENGINE_ID}) を確認してください。"
        else:
             error_message += "リクエスト内容や設定を確認してください。"
        return error_message
    except Exception as e:
        error_message_detail = f"予期せぬエラーが発生しました during search for query '{query}': {e}"
        return f"予期せぬエラーが発生しました: {e}"