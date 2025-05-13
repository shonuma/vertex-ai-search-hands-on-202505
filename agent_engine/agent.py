import os

from dotenv import load_dotenv
from google.adk import Agent
from agent_engine.vais import search_vertex_ai
from typing import Optional, List, Dict

from google.adk.tools.tool_context import ToolContext

load_dotenv()

# tool
def retrieve_from_vais(
    tool_context: ToolContext,
    queries: List[str]
) -> dict[str, str]:
    histories = tool_context.state.get("history", [])
    tool_context.state["history"] = histories + queries

    query_ = queries[0]

    result = search_vertex_ai(query_)
    tool_context.state["result"] = result

    return {"status": "success"}


# agent
root_agent = Agent(
    name="Jirei_Agent",
    description="Google Cloud の顧客事例を教えてくれるエージェントです。",
    model=os.getenv("MODEL", "gemini-2.0-flash-exp"),
    instruction="""
あなたはGoogle Cloud の顧客事例を説明するエージェントです。
挨拶には丁寧に回答し、どのような役割を持つエージェントかを説明します。
[1] 顧客事例に関する質問を受けた場合「xxの事例」という形式で質問内容を要約し、ツールを利用して検索を行い、
{{ result? }} を要約して回答を行ってください。

例）
生成 AI の事例 -> 生成 AI が用いられた事例

以下のように「事例」が省略された場合でも、事例と判断できる文字列であればツールを利用して検索を行ってください。

例）
ゲーム -> ゲームで Google Cloud が利用された事例、ゲーム業界の事例
お客様名、会社名 -> 該当の顧客の事例
BigQuery -> BigQuery が利用された事例
自治体 -> 自治体での事例

[2] 事例以外に関する質問は「事例に関する質問を行ってください」と回答します。


また、回答されたクエリの内容から、おすすめの検索内容を最大3つ提案してください。
""",
    tools=[retrieve_from_vais]
)