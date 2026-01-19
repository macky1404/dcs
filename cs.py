import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
import pandas as pd

# ========================================================
# PAGE CONFIG - Must be first Streamlit command
# ========================================================
st.set_page_config(
    page_title="CS AI Assistant",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================================
# CUSTOM CSS - Modern CS Department Theme
# ========================================================
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main container padding */
    .main > div {
        padding-top: 2rem;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.2);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.95);
        margin: 0.75rem 0 0 0;
        font-size: 1rem;
        font-weight: 400;
    }
    
    /* Info cards */
    .stAlert {
        border-radius: 12px;
        border: none;
        padding: 1rem 1.25rem;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    /* Chat message styling */
    .stChatMessage {
        background-color: transparent !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
    }
    
    [data-testid="stChatMessageContent"] {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 1rem 1.25rem;
    }
    
    /* User message */
    [data-testid="user"] [data-testid="stChatMessageContent"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Assistant message */
    [data-testid="assistant"] [data-testid="stChatMessageContent"] {
        background-color: white;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Chat input container */
    .stChatInputContainer {
        border-top: 1px solid #e9ecef;
        padding-top: 1.5rem;
        background: white;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
        border-right: 1px solid #e9ecef;
    }
    
    [data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }
    
    /* Metric cards */
    [data-testid="metric-container"] {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        border: 1px solid #e9ecef;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
        border: 1px solid #e9ecef;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        border-color: #667eea;
    }
    
    /* Example question buttons */
    .stButton button {
        background-color: white;
        color: #333;
        text-align: left;
    }
    
    /* Clear chat button */
    .stButton button[kind="secondary"] {
        background-color: #fff5f5;
        color: #dc3545;
        border-color: #fecaca;
    }
    
    /* Slider */
    .stSlider {
        padding: 0.5rem 0;
    }
    
    /* Checkbox */
    .stCheckbox {
        padding: 0.5rem 0;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 8px;
        font-weight: 500;
        border: 1px solid #e9ecef;
    }
    
    .streamlit-expanderHeader:hover {
        background-color: #e9ecef;
    }
    
    .streamlit-expanderContent {
        border: 1px solid #e9ecef;
        border-top: none;
        border-radius: 0 0 8px 8px;
        padding: 1rem;
    }
    
    /* Code blocks */
    code {
        background-color: #f1f3f5;
        padding: 0.2rem 0.5rem;
        border-radius: 6px;
        color: #667eea;
        font-size: 0.9em;
        font-weight: 500;
    }
    
    /* Dividers */
    hr {
        margin: 1.5rem 0;
        border: none;
        border-top: 1px solid #e9ecef;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: #d1fae5;
        border-left: 4px solid #10b981;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stError {
        background-color: #fee2e2;
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }
    
    /* Caption */
    .caption {
        color: #6c757d;
        font-size: 0.875rem;
    }
    
    /* Avatar styling */
    [data-testid="chatAvatarIcon"] {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ========================================================
# SETTINGS
# ========================================================
CS_TABLE_PATH = "CS.CS_SCHEMA.CS_TABLE"

@st.cache_resource
def init_connection():
    try:
        return get_active_session()
    except Exception:
        return Session.builder.configs({
            "account": st.secrets["snowflake"]["account"],
            "user": st.secrets["snowflake"]["user"],
            "password": st.secrets["snowflake"]["password"],
            "warehouse": st.secrets["snowflake"]["warehouse"],
            "database": "CS",
            "schema": "CS_SCHEMA",
            "role": st.secrets["snowflake"].get("role", "ACCOUNTADMIN")
        }).create()

session = init_connection()

# ========================================================
# SIDEBAR
# ========================================================
with st.sidebar:
    st.markdown("### 💻 CS Assistant")
    st.caption("Your intelligent academic companion")
    st.markdown("")
    
    st.markdown("#### 📊 Session Overview")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Questions", len([m for m in st.session_state.messages if m["role"] == "user"]))
    with col2:
        st.metric("Responses", len([m for m in st.session_state.messages if m["role"] == "assistant"]))
    
    st.markdown("---")
    
    st.markdown("#### ⚙️ Settings")
    top_k = st.slider("Context Results", min_value=1, max_value=5, value=3, 
                      help="Number of similar questions to retrieve")
    show_sources = st.checkbox("Show Source Context", value=True,
                               help="Display the retrieved knowledge base entries")
    
    st.markdown("---")
    
    st.markdown("#### 💡 Quick Start")
    st.caption("Try these example questions:")
    st.markdown("")
    
    example_questions = [
        "📋 CS program requirements",
        "✍️ Course registration",
        "🕐 Office hours info",
        "🔬 Research opportunities"
    ]
    
    for eq in example_questions:
        if st.button(eq, key=f"ex_{eq}", use_container_width=True):
            st.session_state.example_question = eq.split(" ", 1)[1]
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat", type="secondary", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.caption("⚡ Powered by Snowflake Cortex AI")

# ========================================================
# MAIN HEADER
# ========================================================
st.markdown("""
<div class="main-header">
    <h1>💻 Computer Science AI Assistant</h1>
    <p>Get instant answers from our official knowledge base • Powered by advanced semantic search</p>
</div>
""", unsafe_allow_html=True)

# Quick info cards
col1, col2, col3 = st.columns(3)
with col1:
    st.info("🤖 **AI-Powered**\n\nSemantic search technology")
with col2:
    st.info("📚 **Official Info**\n\nDepartment knowledge base")
with col3:
    st.info("⚡ **Real-time**\n\nInstant responses")

st.markdown("")

# ========================================================
# FUNCTIONS
# ========================================================
def retrieve_context(user_input: str, top_k: int = 3) -> pd.DataFrame:
    safe_input = user_input.replace("'", "''")
    sql = f"""
        WITH q AS (
            SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768(
                'snowflake-arctic-embed-m',
                '{safe_input}'
            ) AS emb
        )
        SELECT
            QUESTION,
            ANSWER,
            VECTOR_COSINE_SIMILARITY(QUESTION_EMBED, q.emb) AS score
        FROM {CS_TABLE_PATH}, q
        ORDER BY score DESC
        LIMIT {top_k}
    """
    return session.sql(sql).to_pandas()

def build_prompt(context_df: pd.DataFrame, user_question: str) -> str:
    if context_df.empty:
        context_text = "No relevant department reference was found."
    else:
        context_text = "\n\n".join(
            f"Q: {row['QUESTION']}\nA: {row['ANSWER']}"
            for _, row in context_df.iterrows()
        )
    return f"""
You are an AI academic assistant for a university Department of Computer Science.
Answer the student question using ONLY the official department references provided.
Be helpful, concise, and professional.

### Department References
{context_text}

### Student Question
{user_question}
"""

# ========================================================
# CHAT INTERFACE
# ========================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "context" in msg and show_sources:
            with st.expander("📚 View Source Context"):
                for j, ctx in enumerate(msg["context"], 1):
                    st.markdown(f"**Source {j}** · Relevance: `{ctx['score']:.1%}`")
                    st.markdown(f"**Q:** {ctx['question']}")
                    st.markdown(f"**A:** {ctx['answer']}")
                    if j < len(msg["context"]):
                        st.markdown("---")

# Handle example question from sidebar
if "example_question" in st.session_state:
    prompt = st.session_state.example_question
    del st.session_state.example_question
else:
    prompt = st.chat_input("💬 Ask me anything about the CS department...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🔍 Searching knowledge base..."):
            try:
                # Retrieve context
                context_df = retrieve_context(prompt, top_k=top_k)
                
                # Build prompt
                ai_prompt = build_prompt(context_df, prompt).replace("'", "''")
                
                # Get response
                query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', '{ai_prompt}') AS RESPONSE"
                result = session.sql(query).collect()
                response = result[0]["RESPONSE"]
                
                st.markdown(response)
                
                # Store context for display
                context_list = []
                if not context_df.empty:
                    for _, row in context_df.iterrows():
                        context_list.append({
                            "question": row['QUESTION'],
                            "answer": row['ANSWER'],
                            "score": row['SCORE']
                        })
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "context": context_list
                })
                
                # Show sources inline if enabled
                if show_sources and context_list:
                    with st.expander("📚 View Source Context"):
                        for j, ctx in enumerate(context_list, 1):
                            st.markdown(f"**Source {j}** · Relevance: `{ctx['score']:.1%}`")
                            st.markdown(f"**Q:** {ctx['question']}")
                            st.markdown(f"**A:** {ctx['answer']}")
                            if j < len(context_list):
                                st.markdown("---")
                
            except Exception as e:
                error_msg = f"I encountered an error while processing your request: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.markdown("---")
st.caption("💡 **Tip:** Be specific with your questions for the most accurate results. The AI uses semantic search to find relevant information.")
