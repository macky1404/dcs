import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd

# ========================================================
# SETTINGS
# ========================================================
# This matches the database and table we built in your new account
CS_TABLE_PATH = "CS.CS_SCHEMA.CS_TABLE" 

# Use the session already active in your Snowflake account
session = get_active_session()

# ========================================================
# APP HEADER
# ========================================================
st.set_page_config(page_title="CS AI Assistant", layout="centered")
st.title("💻 CS Department – AI Academic Assistant")
st.markdown("---")
st.caption("Powered by Snowflake Cortex: Semantic Search & RAG")

# ========================================================
# SEMANTIC RETRIEVAL (RAG ENGINE)
# ========================================================
def retrieve_context(user_input: str, top_k: int = 3) -> pd.DataFrame:
    # We use 'multilingual-e5-large' because it works in almost every region
    # and matches the 768 vector size we used in SQL.
    safe_input = user_input.replace("'", "''")

    sql = f"""
        WITH q AS (
            SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_1024(
                'multilingual-e5-large', 
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
        context_text = "No relevant department records found."
    else:
        context_text = "\n\n".join(
            f"Fact {i+1}: {row['ANSWER']}"
            for i, row in context_df.iterrows()
        )

    return f"""
    You are a professional Academic Assistant for the Computer Science Department.
    Use the following department facts to answer the student's question accurately.
    If the answer is not in the facts, politely tell the student to contact the department office.

    DEPARTMENT FACTS:
    {context_text}

    STUDENT QUESTION:
    {user_question}
    """

# ========================================================
# CHAT INTERFACE
# ========================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask a question about the CS Department..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Assistant Response
    with st.chat_message("assistant"):
        with st.spinner("Consulting Department Knowledge Base..."):
            try:
                # 1. Search for the most relevant facts (Retrieval)
                context_df = retrieve_context(prompt)
                
                # 2. Build the detailed instruction for the AI (Augmentation)
                ai_prompt = build_prompt(context_df, prompt).replace("'", "''")

                # 3. Get the natural language answer (Generation)
                # Using 'mistral-large2' which is standard in Snowflake Cortex
                query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', '{ai_prompt}') AS RESPONSE"
                result = session.sql(query).collect()
                response = result[0]["RESPONSE"]

                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.info("Check if your SQL table has the 'QUESTION_EMBED' column filled.")
