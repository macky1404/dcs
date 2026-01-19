import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
import pandas as pd

# ========================================================
# 1. PAGE CONFIG
# ========================================================
st.set_page_config(
    page_title="CS AI Assistant",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================================
# 2. EMERGENCY VISIBILITY CSS (Fixed for Ghosting)
# ========================================================
st.markdown("""
<style>
    /* Force visibility for sidebar elements */
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p {
        color: var(--text-color) !important;
    }

    /* Fix invisible Metric numbers */
    [data-testid="stMetricValue"] {
        color: #3b82f6 !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-color) !important;
    }

    /* Modern Header with high contrast */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white !important;
        text-align: center;
        margin-bottom: 2rem;
    }
    .main-header h1 { color: white !important; margin-bottom: 5px; }
    .main-header p { color: rgba(255,255,255,0.8) !important; }

    /* Chat styling that adapts to theme */
    [data-testid="stChatMessage"] {
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# ========================================================
# 3. SETTINGS & CONNECTION
# ========================================================
CS_TABLE_PATH = "CS.CS_SCHEMA.CS_TABLE"

@st.cache_resource
def init_connection():
    try:
        return get_active_session()
    except Exception:
        # Assumes st.secrets is configured for local testing
        return Session.builder.configs(st.secrets["snowflake"]).create()

session = init_connection()

# ========================================================
# 4. SIDEBAR (Fixed Visibility)
# ========================================================
with st.sidebar:
    st.title("💻 CS Assistant")
    st.caption("v2.0 Official Knowledge Base")
    
    st.divider()
    
    # Session Stats
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    user_msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Questions", user_msg_count)
    with col2:
        st.metric("Mode", "Cortex AI")

    st.divider()

    st.subheader("⚙️ Settings")
    top_k = st.slider("Search Depth", 1, 5, 3, help="Number of sources to retrieve.")
    show_sources = st.toggle("Show Source Context", value=True)

    st.divider()

    st.subheader("💡 Suggestions")
    examples = ["📋 CS requirements", "✍️ Course registration", "🕐 Office hours"]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            # Clean the icon before storing the prompt
            st.session_state.active_prompt = ex.split(" ", 1)[1]

    if st.button("🗑️ Clear Chat History", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ========================================================
# 5. MAIN INTERFACE
# ========================================================
st.markdown("""
<div class="main-header">
    <h1>Computer Science AI Assistant</h1>
    <p>Semantic search across official department documentation</p>
</div>
""", unsafe_allow_html=True)

# Retrieval Functions
def retrieve_context(user_input: str, k: int):
    safe_input = user_input.replace("'", "''")
    sql = f"""
        WITH q AS (
            SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('snowflake-arctic-embed-m', '{safe_input}') AS emb
        )
        SELECT QUESTION, ANSWER, VECTOR_COSINE_SIMILARITY(QUESTION_EMBED, q.emb) AS score
        FROM {CS_TABLE_PATH}, q
        ORDER BY score DESC LIMIT {k}
    """
    return session.sql(sql).to_pandas()

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "context" in msg and show_sources:
            with st.expander("📚 View Sources"):
                for row in msg["context"]:
                    st.write(f"**Q:** {row['question']} (Similarity: {row['score']:.1%})")
                    st.caption(row['answer'])

# Input Logic
prompt = st.chat_input("Ask about the CS Department...")

# If an example button was clicked, use that instead
if "active_prompt" in st.session_state:
    prompt = st.session_state.active_prompt
    del st.session_state.active_prompt

if prompt:
    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Assistant Message
    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            try:
                context_df = retrieve_context(prompt, top_k)
                context_text = "\n\n".join([f"Source: {r['ANSWER']}" for _, r in context_df.iterrows()])
                
                # Build Prompt for Cortex
                ai_prompt = f"""Use the following context to answer the student:
                Context: {context_text}
                Student Question: {prompt}
                Answer:"""
                
                # Execute Cortex LLM call
                query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', '{ai_prompt.replace(chr(39), chr(39)*2)}')"
                response = session.sql(query).collect()[0][0]
                
                st.markdown(response)
                
                # Save Context for later viewing
                context_list = [{"question": r['QUESTION'], "answer": r['ANSWER'], "score": r['SCORE']} for _, r in context_df.iterrows()]
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response,
                    "context": context_list
                })
                
                if show_sources:
                    with st.expander("📚 View Sources"):
                        for item in context_list:
                            st.write(f"**Q:** {item['question']} ({item['score']:.1%})")
                            st.caption(item['answer'])

            except Exception as e:
                st.error(f"Error processing request: {str(e)}")

st.divider()
st.caption("Powered by Snowflake Cortex AI • CS Department Documentation")
