import streamlit as st
from chatbot import chatbot, getThreadIds, deleteThread
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid


# ----------------- Utilities -----------------
def generate_thread_id():
    """Generates a unique thread ID for the chat session."""
    return str(uuid.uuid4())

def generate_chat_title(first_user_msg: str) -> str:
    """Make a short title from the first user message."""
    words = first_user_msg.strip().split()
    short = " ".join(words[:6])  # take first 6 words
    return short + ("…" if len(words) > 6 else "")



def add_thread_id(thread_id: str,title: str = "New Chat"):
    """Insert new chats at the top (new → old order)."""
    if thread_id not in st.session_state.chat_threads:
        st.session_state.chat_threads.insert(0, {"id": thread_id, "title": title})


def create_new_chat():
    """Creates a new chat session by resetting the messages."""
    thread_id = generate_thread_id()
    st.session_state.thread_id = thread_id
    new_chat = {"id": thread_id, "title": "New Chat"}
    st.session_state.chat_threads.insert(0, new_chat)  # newest at top
    st.session_state.messages = []



def load_chat_history(thread_id: str):
    """Loads chat history and restores saved tool status."""
    messages = chatbot.get_state(
        config={"configurable": {"thread_id": thread_id}}
    ).values.get("messages", [])

    temp_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            temp_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, ToolMessage):
            temp_messages.append(
                {"role": "tool", "content": f"🔧 Tool used: {msg.name or 'Unknown'} ✅"}
            )
        elif isinstance(msg, AIMessage):
            temp_messages.append({"role": "assistant", "content": msg.content})
            # Restore saved tool status if available
            tool_status_key = f"tool_status_{thread_id}_{len(temp_messages)}"
            if tool_status_key in st.session_state:
                status_info = st.session_state[tool_status_key]
                st.status(
                    label=status_info["label"],
                    state=status_info["state"],
                    expanded=status_info["expanded"],
                )
    st.session_state.messages = temp_messages


# ----------------- Streamlit Page -----------------
st.set_page_config(page_title="LangGraph Chatbot", page_icon="🤖", layout="wide")
st.title("🤖 Chatbot Using LangGraph Workflows")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = generate_thread_id()
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = [
        {"id": tid, "title": "New Chat"} for tid in getThreadIds()
    ]

add_thread_id(st.session_state.thread_id)

config = {
    "configurable": {"thread_id": st.session_state.thread_id},
    "metadata": {"thread_id": st.session_state.thread_id},
    "run_name": "chatbot_run",
}

# ----------------- Sidebar -----------------
with st.sidebar:
    st.header("💬 Chats")

    if st.button("➕ New Chat", use_container_width=True):
        create_new_chat()
        st.rerun()

    for chat in st.session_state.chat_threads:
        thread_id = chat["id"]
        title = chat["title"]

        is_active = (thread_id == st.session_state.thread_id)
        chat_icon = "👉" if is_active else "💬"
        button_label = f"{chat_icon} {title}"

        row = st.container()
        col1, col2 = row.columns([0.85, 0.15])

        with col1:
            if st.button(button_label, key=f"open_{thread_id}", use_container_width=True):
                st.session_state.thread_id = thread_id
                load_chat_history(thread_id)
                st.rerun()

        with col2:
            if st.button("🗑️", key=f"delete_{thread_id}", use_container_width=True):
                if deleteThread(thread_id):
                    st.session_state.chat_threads = [
                        c for c in st.session_state.chat_threads if c["id"] != thread_id
                    ]
                    if thread_id == st.session_state.thread_id:
                        create_new_chat()
                    st.rerun()




# ----------------- Chat Messages -----------------
for message in st.session_state["messages"]:
    with st.chat_message("assistant" if message["role"] == "tool" else message["role"]):
        if message["role"] == "tool":
            st.info(message["content"])
        else:
            st.markdown(message["content"])

# ----------------- Chat Input -----------------
user_input = st.chat_input("Type your message here...")

if user_input:
    # Show user input
    with st.chat_message("user"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.markdown(user_input)

    # Assistant response with streaming
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
                # Handle tool messages
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
                # Yield assistant tokens
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        # Store tool completion state
        if status_holder["box"] is not None:
            st.session_state[tool_status_key] = {
                "label": "✅ Tool finished",
                "state": "complete",
                "expanded": False,
            }
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )

    st.session_state["messages"].append({"role": "assistant", "content": ai_message})
    active_chat = next(
        (c for c in st.session_state.chat_threads if c["id"] == st.session_state.thread_id),
        None,
    )
    if active_chat and active_chat["title"] == "New Chat":
        active_chat["title"] = generate_chat_title(user_input)
