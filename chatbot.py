from langgraph.graph import START, END, StateGraph
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from dotenv import load_dotenv
import sqlite3

# Load environment variables from .env file
load_dotenv()

class ChatbotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

llm = ChatOpenAI()

# Tools
search_tool = DuckDuckGoSearchRun(region="us-en")

tools = [search_tool]
llm_with_tools = llm.bind_tools(tools)

def run_chatbot(state: ChatbotState) -> str:
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": messages + [response]}

tool_node = ToolNode(tools)

connection = sqlite3.connect(database="chatbot_state.db", check_same_thread=False)
checkpointer = SqliteSaver(connection)
graph = StateGraph(ChatbotState)

graph.add_node("chatbot_node", run_chatbot)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chatbot_node")
graph.add_conditional_edges("chatbot_node",tools_condition)
graph.add_edge('tools', 'chatbot_node')

chatbot = graph.compile(checkpointer=checkpointer)


def getThreadIds():
    all_threads= set()
    for state in checkpointer.list(None):
        all_threads.add(state.config['configurable']['thread_id'])
    return list(all_threads)
    
    
def deleteThread(thread_id):
    try:
        print(f"Attempting to delete thread: {thread_id}")  # Debug log
        success = checkpointer.delete_thread(thread_id)
        print(f"Delete success: {success}")  # Debug log
        return True
    except Exception as e:
        print(f"Error deleting thread: {e}")
        return False