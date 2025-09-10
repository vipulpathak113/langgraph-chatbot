from langgraph.graph import START, END, StateGraph
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from dotenv import load_dotenv
import sqlite3

# Load environment variables from .env file
load_dotenv()

class ChatbotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

llm = ChatOpenAI()

# Tools
search_tool = DuckDuckGoSearchRun(
    region="us-en",
    max_results=5,  # Increase number of results
    kwargs={
        "time": "m",  # Get recent results from last month
    }
)
tools = [search_tool]
llm_with_tools = llm.bind_tools(tools)

def run_chatbot(state: ChatbotState) -> str:
    messages = state["messages"]
    # Add system message to encourage tool usage
    system_message = {
        "role": "system",
        "content": """When you're not completely sure about information or need real-time data, 
        use the search tool. For AI-related queries, always verify information through search first.
        Available tools: DuckDuckGoSearch - Use this to search for current information."""
    }
    
    if not any(msg.type == "system" for msg in messages):
        messages = [SystemMessage(content=system_message["content"])] + messages
        
    response = llm_with_tools.invoke(messages)
    return {"messages": messages + [response]}

tool_node = ToolNode(tools)

connection = sqlite3.connect(database="chatbot_state.db", check_same_thread=False)
checkpointer = SqliteSaver(connection)

# --- Ensure chat_titles table exists ---
with connection:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS chat_titles (
            thread_id TEXT PRIMARY KEY,
            title TEXT
        )
    """)

graph = StateGraph(ChatbotState)
graph.add_node("chatbot_node", run_chatbot)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chatbot_node")
graph.add_conditional_edges("chatbot_node", tools_condition)
graph.add_edge("tools", "chatbot_node")
chatbot = graph.compile(checkpointer=checkpointer)

# --- New helper functions for titles ---
def saveThreadTitle(thread_id: str, title: str):
    """Save or update chat title in SQLite"""
    with connection:
        connection.execute(
            "INSERT OR REPLACE INTO chat_titles (thread_id, title) VALUES (?, ?)",
            (thread_id, title)
        )

def getThreadIds():
    """Return all threads with titles"""
    all_threads = []
    for state in checkpointer.list(None):
        tid = state.config['configurable']['thread_id']
        # Try to fetch title
        cur = connection.execute(
            "SELECT title FROM chat_titles WHERE thread_id = ?", (tid,)
        )
        row = cur.fetchone()
        title = row[0] if row else "New Chat"
        all_threads.append({"id": tid, "title": title})
    return all_threads

def deleteThread(thread_id: str):
    try:
        print(f"Attempting to delete thread: {thread_id}")
        success = checkpointer.delete_thread(thread_id)
        with connection:
            connection.execute(
                "DELETE FROM chat_titles WHERE thread_id = ?", (thread_id,)
            )
        print(f"Delete success: {success}")
        return True
    except Exception as e:
        print(f"Error deleting thread: {e}")
        return False

def getMessagesForThread(thread_id):
    """Return stored messages for a given thread_id."""
    state = checkpointer.get({"configurable": {"thread_id": thread_id}})
    if state and "messages" in state.values:
        msgs = []
        for m in state.values["messages"]:
            msgs.append({"role": m.type, "content": m.content})
        return msgs
    return []

def updateThreadTitle(thread_id: str, new_title: str):
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE thread_titles SET title = ? WHERE thread_id = ?",
            (new_title, thread_id),
        )
        connection.commit()
        return True
    except Exception as e:
        print(f"Error updating title: {e}")
        return False


def append_message_to_thread(thread_id: str, message):
    """
    Append a message (HumanMessage / AIMessage / ToolMessage) to the saved thread in backend.
    """
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", [])
    messages.append(message)
    chatbot.save_state({"messages": messages}, config={"configurable": {"thread_id": thread_id}})


