import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
import pandas as pd

# ========================================================
# SETTINGS - MATCHING YOUR SQL
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
# APP HEADER
# ========================================================
st.title("💻 CS Department – AI Academic Assistant")
st.caption("Using Snowflake Cortex for Semantic Search and RAG.")

# ========================================================
# SEMANTIC RETRIEVAL (SNOWFLAKE CORTEX)
# ========================================================
def retrieve_context(user_input: str, top_k: int = 3) -> pd.DataFrame:
    safe_input = user_input.replace("'", "''")

    # This query compares the user's question to the vectors in your table
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

# ========================================================
# PROMPT BUILDER
# ========================================================
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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about the CS department..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching CS knowledge base..."):
            try:
                # 1. Get similar questions from your table
                context_df = retrieve_context(prompt)
                
                # 2. Build the AI prompt
                ai_prompt = build_prompt(context_df, prompt).replace("'", "''")

                # 3. Get the final answer from the LLM
                query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', '{ai_prompt}') AS RESPONSE"
                result = session.sql(query).collect()
                response = result[0]["RESPONSE"]

                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                st.error(f"❌ AI Error: {e}")