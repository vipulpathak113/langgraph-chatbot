import streamlit as st
from chatbot import chatbot
from langchain_core.messages import HumanMessage

# Streamlit Chatbot UI Component
# This component allows users to interact with a chatbot in a chat-like interface.
st.title("Chatbot Using LangGraph Workflow")

config = {"configurable": {"thread_id": "thread-1"}}
# Initialize session state for messages if not already present
# Storing in session state as streamlit reset the state on every run
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

user_input = st.chat_input("Type your message here....")

if user_input:
    with st.chat_message("user"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.text(user_input)

    response = chatbot.invoke(
        {"messages": HumanMessage(content=user_input)}, config=config
    )
    ai_response = response["messages"][-1].content

    with st.chat_message("assistant"):
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        st.text(ai_response)
