import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
import pandas as pd

# ========================================================
# PAGE CONFIG
# ========================================================
st.set_page_config(
    page_title="CS AI Assistant",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================================
# REFINED CSS - Focus on Visibility and Modernity
# ========================================================
st.markdown("""
<style>
    /* Global Font and Clean Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main Header Styling */
    .header-container {
        padding: 1.5rem;
        background-color: #4A90E2;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }

    /* Chat Message Improvements */
    [data-testid="stChatMessage"] {
        padding: 1rem;
        border-radius: 15px;
        margin-bottom: 10px;
    }

    /* Improved User Message Contrast */
    [data-testid="user"] {
        background-color: rgba(74, 144, 226, 0.1) !important;
        border: 1px solid rgba(74, 144, 226, 0.2);
    }

    /* Sidebar Clean-up */
    [data-testid="stSidebar"] {
        background-color: #fcfcfc;
    }

    /* Metric Styling */
    [data-testid="stMetric"] {
        background: white;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Source Context Expander Styling */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        color: #4A90E2 !important;
    }
</style>
""", unsafe_allow_html=True)

# ========================================================
# SNOWFLAKE CONNECTION
# ========================================================
CS_TABLE_PATH = "CS.CS_SCHEMA.CS_TABLE"

@st.cache_resource
def init_connection():
    try:
        return get_active_session()
    except Exception:
        # Fallback for local development
        return Session.builder.configs(st.secrets["snowflake"]).create()

session = init_connection()

# ========================================================
# SIDEBAR - Clean and Functional
# ========================================================
with st.sidebar:
    st.title("💻 CS Assistant")
    st.caption("v2.0 • Intelligent Academic Support")
    
    st.divider()
    
    # Session Metrics in an organized grid
    st.subheader("📊 Statistics")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    m_col1, m_col2 = st.columns(2)
    user_msgs = len([m for m in st.session_state.messages if m["role"] == "user"])
    m_col1.metric("Questions", user_msgs)
    m_col2.metric("Tokens", f"{user_msgs * 1.2:.1f}k") # Approximation

    st.divider()

    st.subheader("⚙️ Configuration")
    top_k = st.slider("Context Depth", 1, 5, 3, help="How many knowledge base articles to look at.")
    show_sources = st.toggle("Show Research Sources", value=True)

    st.divider()

    st.subheader("💡 Suggestions")
    examples = ["📋 Program Requirements", "✍️ Course Registration", "🕐 Office Hours"]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.active_prompt = ex.split(" ", 1)[1]

    if st.button("🗑️ Reset Conversation", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ========================================================
# MAIN UI
# ========================================================
st.markdown("""
    <div class="header-container">
        <h1 style='margin:0;'>CS Academic Assistant</h1>
        <p style='margin:0; opacity: 0.9;'>Official Department Knowledge Base</p>
    </div>
    """, unsafe_allow_html=True)

# Helper Functions
def retrieve_context(user_input: str, top_k: int = 3):
    safe_input = user_input.replace("'", "''")
    sql = f"""
        WITH q AS (
            SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('snowflake-arctic-embed-m', '{safe_input}') AS emb
        )
        SELECT QUESTION, ANSWER, VECTOR_COSINE_SIMILARITY(QUESTION_EMBED, q.emb) AS score
        FROM {CS_TABLE_PATH}, q
        ORDER BY score DESC LIMIT {top_k}
    """
    return session.sql(sql).to_pandas()

# Chat Display
if not st.session_state.messages:
    st.info("👋 **Welcome!** Ask a question about the CS department curriculum, faculty, or facilities to get started.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "context" in msg and show_sources:
            with st.expander("🔍 View Sources"):
                for i, row in enumerate(msg["context"]):
                    st.write(f"**{i+1}. {row['question']}** (Match: {row['score']:.1%})")
                    st.caption(row['answer'])

# Chat Input Logic
prompt = st.chat_input("How can I help you today?")
if "active_prompt" in st.session_state:
    prompt = st.session_state.active_prompt
    del st.session_state.active_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consulting knowledge base..."):
            try:
                context_df = retrieve_context(prompt, top_k)
                context_str = "\n".join([f"Q: {r['QUESTION']}\nA: {r['ANSWER']}" for _, r in context_df.iterrows()])
                
                # Snowflake Cortex Call
                llm_prompt = f"Using this context: {context_str}\n\nQuestion: {prompt}\nAnswer professionally:"
                response = session.sql(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', '{llm_prompt.replace(chr(39), chr(39)*2)}')").collect()[0][0]
                
                st.markdown(response)
                
                # Save to history
                history_entry = {
                    "role": "assistant", 
                    "content": response,
                    "context": [{"question": r['QUESTION'], "answer": r['ANSWER'], "score": r['SCORE']} for _, r in context_df.iterrows()]
                }
                st.session_state.messages.append(history_entry)
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.divider()
st.caption("Powered by Snowflake Cortex AI • CS Department v2026")
