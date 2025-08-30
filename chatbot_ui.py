import streamlit as st
from chatbot import chatbot,getThreadIds,deleteThread
from langchain_core.messages import HumanMessage,AIMessage,ToolMessage
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
    """Loads chat history and restores any saved tool status"""
    messages = chatbot.get_state(config={"configurable": {"thread_id": thread_id}}).values.get("messages", [])
    temp_messages = []
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            temp_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            temp_messages.append({"role": "assistant", "content": msg.content})
            # Check if there was a tool status saved for this message
            tool_status_key = f"tool_status_{thread_id}_{len(temp_messages)}"
            if tool_status_key in st.session_state:
                status_info = st.session_state[tool_status_key]
                # Create status box with saved state
                st.status(
                    label=status_info["label"],
                    state=status_info["state"],
                    expanded=status_info["expanded"]
                )
    
    st.session_state.messages = temp_messages
    return messages


# Initialize session state for messages if not already present
# Storing in session state as streamlit reset the state on every run
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "thread_id" not in st.session_state:
    st.session_state.thread_id = generateThreadId()    
    
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = getThreadIds()    
    
add_thread_id(st.session_state.thread_id)    

config = {"configurable": {"thread_id": st.session_state.thread_id},"metadata": {"thread_id": st.session_state.thread_id},"run_name":"chatbot_run"}

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

    # Assistant streaming block
    with st.chat_message("assistant"):
        message_index = len(st.session_state.messages)
        tool_status_key = f"tool_status_{st.session_state.thread_id}_{message_index}"
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
                stream_mode="messages",
            ):
                # Lazily create & update the SAME status container when any tool runs
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                # Stream ONLY assistant tokens
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        # Store the tool status in session state with unique key per message
        if status_holder["box"] is not None:
            st.session_state[tool_status_key] = {
                "label": "✅ Tool finished",
                "state": "complete",
                "expanded": False
            }
            status_holder["box"].update(
                label="✅ Tool finished",
                state="complete",
                expanded=False
            )

    st.session_state["messages"].append(
        {"role": "assistant", "content": ai_message}
    )
