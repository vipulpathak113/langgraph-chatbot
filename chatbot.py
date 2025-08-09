from langgraph.graph import START, END, StateGraph
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
import sqlite3

# Load environment variables from .env file
load_dotenv()

class ChatbotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

llm = ChatOpenAI()

def run_chatbot(state: ChatbotState) -> str:
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": messages + [response]}

connection = sqlite3.connect(database="chatbot_state.db", check_same_thread=False)
checkpointer = SqliteSaver(connection)
graph = StateGraph(ChatbotState)

graph.add_node("chatbot", run_chatbot)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

chatbot = graph.compile(checkpointer=checkpointer)


def getThreadIds():
    all_threads= set()
    for state in checkpointer.list(None):
        all_threads.add(state.config['configurable']['thread_id'])
    return list(all_threads)
    
    