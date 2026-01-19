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
# CUSTOM CSS - CS Department Theme
# ========================================================
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --cs-primary: #0066cc;
        --cs-secondary: #00cc88;
        --cs-accent: #ff6b35;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    /* Stats cards */
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
        margin: 0;
    }
    
    .stat-label {
        color: #666;
        font-size: 0.9rem;
        margin: 0;
    }
    
    /* Chat styling */
    .stChatMessage {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Source context box */
    .context-box {
        background: #f0f7ff;
        border-left: 4px solid #0066cc;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-size: 0.9rem;
    }
    
    /* Input styling */
    .stChatInputContainer {
        border-top: 2px solid #667eea;
        padding-top: 1rem;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Code block styling */
    code {
        background-color: #f4f4f4;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
        color: #e83e8c;
    }
    
    /* Success/Error messages */
    .stAlert {
        border-radius: 8px;
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
    st.image("https://api.dicebear.com/7.x/shapes/svg?seed=cs-logo", width=100)
    st.title("🎓 CS Assistant")
    st.markdown("---")
    
    st.subheader("📊 Session Stats")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Questions", len([m for m in st.session_state.messages if m["role"] == "user"]))
    with col2:
        st.metric("Responses", len([m for m in st.session_state.messages if m["role"] == "assistant"]))
    
    st.markdown("---")
    
    st.subheader("⚙️ Settings")
    top_k = st.slider("Context Results", min_value=1, max_value=5, value=3, 
                      help="Number of similar questions to retrieve")
    show_sources = st.checkbox("Show Source Context", value=True,
                               help="Display the retrieved knowledge base entries")
    
    st.markdown("---")
    
    st.subheader("💡 Example Questions")
    example_questions = [
        "What are the CS program requirements?",
        "How do I register for courses?",
        "What are office hours?",
        "Tell me about research opportunities"
    ]
    
    for eq in example_questions:
        if st.button(eq, key=f"ex_{eq}", use_container_width=True):
            st.session_state.example_question = eq
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.caption("Powered by Snowflake Cortex AI")

# ========================================================
# MAIN HEADER
# ========================================================
st.markdown("""
<div class="main-header">
    <h1>💻 Computer Science Department</h1>
    <p>AI-Powered Academic Assistant | Instant answers from our knowledge base</p>
</div>
""", unsafe_allow_html=True)

# Quick info cards
col1, col2, col3 = st.columns(3)
with col1:
    st.info("🤖 **AI-Powered**: Using advanced semantic search")
with col2:
    st.info("📚 **Knowledge Base**: Official CS department information")
with col3:
    st.info("⚡ **Real-time**: Instant responses to your questions")

st.markdown("---")

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
                    st.markdown(f"**Source {j}** (Similarity: {ctx['score']:.2%})")
                    st.markdown(f"*Q: {ctx['question']}*")
                    st.markdown(f"A: {ctx['answer']}")
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
                            st.markdown(f"**Source {j}** (Similarity: {ctx['score']:.2%})")
                            st.markdown(f"*Q: {ctx['question']}*")
                            st.markdown(f"A: {ctx['answer']}")
                            if j < len(context_list):
                                st.markdown("---")
                
                st.success("✅ Response generated successfully!")
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.markdown("---")
st.caption("💡 Tip: Be specific with your questions for the best results. The AI uses semantic search to find relevant information from the CS department knowledge base.")
