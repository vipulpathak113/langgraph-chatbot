import streamlit as st
from chatbot import chatbot,getThreadIds,deleteThread
from langchain_core.messages import HumanMessage
import uuid

# Streamlit Chatbot UI Component
# This component allows users to interact with a chatbot in a chat-like interface.
st.title("Chatbot Using LangGraph Workflows")

def generateThreadId():
    """Generates a unique thread ID for the chat session."""
    return str(uuid.uuid4()) 

def add_thread_id(thread_id):
    if thread_id not in st.session_state.chat_threads:
        st.session_state.chat_threads.append(thread_id)

def create_new_chat():
    """Creates a new chat session by resetting the messages."""
    thread_id= generateThreadId()
    st.session_state.thread_id = thread_id
    add_thread_id(thread_id)
    st.session_state.messages = []
    
def load_chat_history(thread_id):
    return chatbot.get_state(config={"configurable": {"thread_id": thread_id}}).values.get("messages", [])  


# Initialize session state for messages if not already present
# Storing in session state as streamlit reset the state on every run
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "thread_id" not in st.session_state:
    st.session_state.thread_id = generateThreadId()    
    
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = getThreadIds()    
    
add_thread_id(st.session_state.thread_id)    

config = {"configurable": {"thread_id": st.session_state.thread_id}}

if st.sidebar.button("New Chat"):
    create_new_chat()

st.sidebar.header("Chats")

# Update the thread listing section
if st.session_state['chat_threads']:
    for thread_id in st.session_state['chat_threads'][::-1]:
        col1, col2 = st.sidebar.columns(2)  # Adjusted ratio
        
        # Thread button
        with col1:
            if st.button(thread_id, key=f"thread_{thread_id}", use_container_width=True):
                st.session_state.thread_id = thread_id
                messages = load_chat_history(thread_id)
                temp_messages = []
                for msg in messages:
                    if isinstance(msg, HumanMessage):
                        temp_messages.append({"role": "user", "content": msg.content})
                    else:
                        temp_messages.append({"role": "assistant", "content": msg.content})
                st.session_state.messages = temp_messages
        
        # Menu using selectbox
        with col2:
            option = st.selectbox(
                "",
                ["Select","Delete"],
                key=f"menu_{thread_id}",
                width=800,
            )
            
            if option == "Delete":
                confirm = st.button("Confirm Delete?", key=f"confirm_{thread_id}")
                if confirm:
                    if deleteThread(thread_id):
                        st.session_state.chat_threads.remove(thread_id)
                        if thread_id == st.session_state.thread_id:
                            create_new_chat()
                        st.session_state.chat_threads = getThreadIds()
                        st.rerun()
                
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

user_input = st.chat_input("Type your message here....")

if user_input:
    with st.chat_message("user"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.text(user_input)

    with st.chat_message("assistant"):
        generator_reponse= chatbot.stream({"messages":HumanMessage(content=user_input)}, config=config, stream_mode="messages");
        ai_response= st.write_stream(message_chunk.content for message_chunk,metadata in generator_reponse)
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
