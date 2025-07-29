from langgraph.graph import START, END, StateGraph
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ChatbotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


llm = ChatOpenAI()


def run_chatbot(state: ChatbotState) -> str:
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": messages + [response]}


checkpointer = MemorySaver()
graph = StateGraph(ChatbotState)
graph.add_node("chatbot", run_chatbot)

graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

chatbot = graph.compile(checkpointer=checkpointer)


# adding conversation to chatbot

thread_id = "1"
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        break
    config = {"configurable": {"thread_id": thread_id}}
    response = chatbot.invoke(
        {"messages": [HumanMessage(content=user_input)]}, config=config
    )
    print("Chatbot:", response["messages"][-1].content)
