from langgraph.graph import START, END, StateGraph
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
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


graph = StateGraph(ChatbotState)
graph.add_node("chatbot", run_chatbot)

graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

chatbot = graph.compile()


# adding conversation to chatbot

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        break
    response = chatbot.invoke({"messages": [HumanMessage(content=user_input)]})
    print("Chatbot:", response["messages"][-1].content)
