import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ---------- Load environment variables ----------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

# ---------- Streamlit page config ----------
st.set_page_config(
    page_title="AI Email Assistant",
    page_icon="📧",
    layout="wide",
)

st.title("AI Email Assistant")
st.caption("⚠️ Do not paste sensitive or private data. This is a demo tool.")
st.write(
    "Paste an email you received, choose tone and length, and let the AI draft a reply for you."
)

if not OPENAI_API_KEY:
    st.error(
        "OPENAI_API_KEY is not set. Please create a `.env` file with your key, e.g.\n\n"
        "`OPENAI_API_KEY=sk-...`"
    )

# ---------- Helper: generate reply using OpenAI ----------
def generate_reply(email_text: str, tone: str, length: str) -> str:
    """
    Generate an email reply using the new OpenAI API (v1+).
    """
    if client is None:
        return "Error: OpenAI client is not configured. Check your API key."

    system_prompt = (
        "You are a helpful AI email assistant. "
        "You write clear, concise, and well-structured email replies. "
        "Always respect the requested tone and length, and keep a professional attitude."
    )

    user_prompt = f"""
    Write a reply to the following email.

    Tone: {tone}
    Length: {length}

    Original email:
    \"\"\"{email_text}\"\"\"
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )

        reply = response.choices[0].message.content.strip()
        return reply

    except Exception as e:
        return f"Error while calling OpenAI API: {e}"

# ---------- Sidebar options ----------
st.sidebar.header("Settings")

tone = st.sidebar.selectbox(
    "Tone",
    options=["Professional", "Friendly", "Assertive", "Neutral"],
    index=0,
)

length = st.sidebar.selectbox(
    "Length",
    options=["Short", "Medium", "Long"],
    index=1,
)

# ---------- Main input area ----------
st.subheader("Paste the original email")
email_text = st.text_area(
    "Email content",
    height=250,
    placeholder="Paste here the email you received...",
)

generate_button = st.button("Generate reply")

st.divider()

# ---------- Handle generation ----------
if generate_button:
    if not email_text.strip():
        st.warning("Please paste an email before generating a reply.")
    elif client is None:
        st.error("OpenAI client is not configured. Check your API key.")
    else:
        with st.spinner("Generating reply..."):
            reply = generate_reply(email_text, tone, length)

        st.subheader("AI-generated reply")
        st.markdown(f"```text\n{reply}\n```")
