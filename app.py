import os
import json
import base64

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

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

st.title("AI Email Assistant – Pro")
st.write(
    "Paste an email, or load one from Gmail (local only), and the AI will analyze it "
    "(summary, sentiment, urgency) and generate multiple reply options based on your preferences."
)

st.caption("⚠️ Do not paste sensitive or personal data. This is a demo tool.")

if not OPENAI_API_KEY:
    st.error(
        "OPENAI_API_KEY is not set. Please configure it in your `.env` "
        "or as a Streamlit secret."
    )

# ---------- Session state init ----------
if "email_text" not in st.session_state:
    st.session_state["email_text"] = ""
if "gmail_messages" not in st.session_state:
    st.session_state["gmail_messages"] = []

# ---------- Gmail API helpers (local use only) ----------

# We only need read-only access to Gmail
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    """
    Returns an authenticated Gmail API service.
    Only works locally with credentials.json present.
    """
    creds = None

    # token.json stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", GMAIL_SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "credentials.json not found. "
                    "Download it from Google Cloud Console and place it in the project folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


def list_gmail_messages(service, max_results=10):
    """
    List last messages in the user's inbox (basic info).
    Returns a list of dicts with id, snippet, and headers (From, Subject).
    """
    results = (
        service.users()
        .messages()
        .list(
            userId="me",
            labelIds=["INBOX"],
            maxResults=max_results,
        )
        .execute()
    )

    messages = results.get("messages", [])

    items = []
    for msg in messages:
        msg_detail = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject"],
            )
            .execute()
        )

        headers = msg_detail.get("payload", {}).get("headers", [])
        header_dict = {h["name"]: h["value"] for h in headers}
        snippet = msg_detail.get("snippet", "")

        items.append(
            {
                "id": msg["id"],
                "from": header_dict.get("From", "Unknown"),
                "subject": header_dict.get("Subject", "(No subject)"),
                "snippet": snippet,
            }
        )

    return items


def get_gmail_message_body(service, message_id: str) -> str:
    """
    Fetch the full body text of a Gmail message.
    Tries to read text/plain first, then text/html as fallback.
    """
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )

    payload = msg.get("payload", {})
    parts = payload.get("parts", [])

    def decode_data(data: str) -> str:
        return (
            base64.urlsafe_b64decode(data.encode("UTF-8"))
            .decode("UTF-8", errors="ignore")
            .strip()
        )

    body_text = ""

    # Single-part email
    if "data" in payload.get("body", {}):
        body_text = decode_data(payload["body"]["data"])
    else:
        # Multi-part: try text/plain first
        for part in parts:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain" and "data" in part.get("body", {}):
                body_text = decode_data(part["body"]["data"])
                break

        # fallback: text/html
        if not body_text:
            for part in parts:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/html" and "data" in part.get("body", {}):
                    body_text = decode_data(part["body"]["data"])
                    break

    return body_text


# ---------- Helper: analyze email + generate replies ----------
def analyze_and_reply(
    email_text: str,
    tone: str,
    formality: str,
    length: str,
    num_options: int,
):
    """
    Use OpenAI to:
    - detect language
    - estimate urgency, sentiment, and category
    - summarize the email
    - extract action items
    - generate N reply options with subject + body

    Returns either:
    - dict with parsed JSON
    - or a string with an error message
    """
    if client is None:
        return "Error: OpenAI client is not configured. Check your API key."

    system_prompt = (
        "You are an advanced AI email assistant. "
        "You help busy professionals understand and reply to emails. "
        "You ALWAYS respond with a single valid JSON object, no extra text. "
        "Your tasks:\n"
        "- Detect the language of the original email and reply in the SAME language.\n"
        "- Estimate urgency: one of ['low', 'medium', 'high'].\n"
        "- Estimate sentiment: one of ['positive', 'neutral', 'negative', 'mixed'].\n"
        "- Classify the email category: e.g. 'inquiry', 'complaint', 'follow_up', 'update', 'other'.\n"
        "- Provide a short summary of the email (2–4 sentences).\n"
        "- Extract a list of concrete action items (tasks the recipient should do).\n"
        "- Generate multiple reply options (subject + body) following the requested tone, formality, and length.\n"
    )

    user_prompt = f"""
You will receive an email and some preferences for the reply.

Email:
\"\"\"{email_text}\"\"\"

Preferences:
- Tone: {tone}
- Formality: {formality}
- Length: {length} 
  (Short = 3–5 sentences, Medium = 6–10 sentences, Long = more detailed)
- Number of reply options: {num_options}

Return ONLY a JSON object with the following EXACT structure (no comments, no extra text):

{{
  "language": "<detected_language_code_or_name>",
  "urgency": "<low|medium|high>",
  "sentiment": "<positive|neutral|negative|mixed>",
  "category": "<short_category_label>",
  "summary": "<short_paragraph_summary>",
  "action_items": [
    "<item_1>",
    "<item_2>"
  ],
  "replies": [
    {{
      "subject": "<suggested_subject_line>",
      "body": "<full_email_body_ready_to_send>"
    }}
  ]
}}

Rules:
- The length and style of each reply must match the user's preferences.
- The number of elements in 'replies' MUST be exactly {num_options}.
- Do NOT include any explanation outside the JSON.
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

        raw_content = response.choices[0].message.content.strip()

        # Try to parse JSON safely
        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError:
            # Sometimes the model may wrap JSON in ```json ... ``` – try to clean
            cleaned = raw_content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                # remove possible "json" prefix
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].strip()
            data = json.loads(cleaned)

        return data

    except Exception as e:
        return f"Error while calling OpenAI API: {e}"


# ---------- Sidebar options ----------
st.sidebar.header("Settings")

tone = st.sidebar.selectbox(
    "Tone",
    options=["Professional", "Friendly", "Assertive", "Neutral"],
    index=0,
)

formality = st.sidebar.selectbox(
    "Formality",
    options=["Very formal", "Formal", "Neutral", "Informal"],
    index=1,
)

length = st.sidebar.selectbox(
    "Length",
    options=["Short", "Medium", "Long"],
    index=1,
)

num_options = st.sidebar.selectbox(
    "Number of reply options",
    options=[1, 2, 3],
    index=1,  # default = 2
)

# ---------- Main input area ----------
st.subheader("Choose input source")

gmail_available = os.path.exists("credentials.json")

options = ["Paste email manually"]
if gmail_available:
    options.append("Gmail inbox (local only)")

input_mode = st.radio(
    "Email source",
    options=options,
    index=0,
)

if not gmail_available:
    st.caption("Gmail mode is available only in the local version (credentials.json not found).")


# Use session_state["email_text"] as the single source of truth
if input_mode == "Paste email manually":
    st.subheader("Paste the original email")
    st.text_area(
        "Email content",
        height=250,
        placeholder="Paste here the email you received...",
        key="email_text",
    )

else:
    st.subheader("Gmail inbox (local only)")
    st.caption(
        "This mode works only on your local machine with Gmail OAuth configured "
        "(credentials.json + token.json)."
    )

    if st.button("Load last emails from Gmail"):
        try:
            service = get_gmail_service()
            messages = list_gmail_messages(service, max_results=10)
            st.session_state["gmail_messages"] = messages
        except Exception as e:
            st.error(f"Error while connecting to Gmail: {e}")

    messages = st.session_state.get("gmail_messages", [])

    if messages:
        options = [
            f'{i+1}. {m["subject"]} — {m["from"]}  |  {m["snippet"][:60]}...'
            for i, m in enumerate(messages)
        ]
        selected = st.selectbox("Select an email", options, index=0)
        selected_index = options.index(selected)
        selected_msg = messages[selected_index]

        if st.button("Use this email"):
            try:
                service = get_gmail_service()
                body = get_gmail_message_body(service, selected_msg["id"])
                st.session_state["email_text"] = body
                st.success(
                    "Email loaded from Gmail into the editor. "
                    "Scroll down and click 'Analyze & generate replies'."
                )
            except Exception as e:
                st.error(f"Error while fetching email body: {e}")
    else:
        st.info("Click 'Load last emails from Gmail' to fetch your inbox.")

email_text = st.session_state.get("email_text", "")
analyze_button = st.button("Analyze & generate replies ✉️")

st.divider()

# ---------- Handle generation ----------
if analyze_button:
    if not email_text.strip():
        st.warning("Please paste an email or load one from Gmail before generating replies.")
    elif client is None:
        st.error("OpenAI client is not configured. Check your API key.")
    else:
        with st.spinner("Analyzing email and generating replies..."):
            result = analyze_and_reply(
                email_text=email_text,
                tone=tone,
                formality=formality,
                length=length,
                num_options=num_options,
            )

        if isinstance(result, str):
            # Error message
            st.error(result)
        else:
            # ---------- Show analysis ----------
            st.subheader("Email analysis")

            lang = result.get("language", "N/A")
            urgency = result.get("urgency", "N/A")
            sentiment = result.get("sentiment", "N/A")
            category = result.get("category", "N/A")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Language", lang)
            with col2:
                st.metric("Urgency", urgency.capitalize())
            with col3:
                st.metric("Sentiment", sentiment.capitalize())
            with col4:
                st.metric("Category", category)

            summary = result.get("summary") or ""
            action_items = result.get("action_items") or []

            if summary:
                st.markdown("### Summary")
                st.write(summary)

            if action_items:
                st.markdown("### Action items")
                for item in action_items:
                    st.markdown(f"- {item}")

            # ---------- Show reply options ----------
            replies = result.get("replies") or []

            if not replies:
                st.warning("No reply options were returned by the AI.")
            else:
                st.markdown("### AI-generated reply options")

                tab_labels = [f"Option {i+1}" for i in range(len(replies))]
                tabs = st.tabs(tab_labels)

                for tab, reply_data in zip(tabs, replies):
                    with tab:
                        subject = reply_data.get("subject", "")
                        body = reply_data.get("body", "")

                        if subject:
                            st.markdown(f"**Subject:** {subject}")

                        st.markdown("**Body:**")
                        st.markdown(f"```text\n{body}\n```")

                        combined = subject + "\n\n" + body if subject else body
                        st.text_area(
                            "Ready to copy",
                            value=combined,
                            height=200,
                        )
