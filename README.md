# AI Email Assistant Pro 📧

AI-powered email assistant built with Streamlit and OpenAI.

You can either paste an email manually **or** (in the local version) load messages directly from your Gmail inbox.  
The app analyzes the email (summary, sentiment, urgency, category) and generates multiple reply options based on your preferences.

---

## 🔗 Live Demo (manual mode only)

Public Streamlit app (paste-only mode):

https://davidetonell-o-ai-email-assistant-app-s4t7hy.streamlit.app/

⚠️ Gmail integration is NOT available in the public deploy due to Google OAuth restrictions.  
Gmail mode works perfectly in the local version.

---

## ✨ Features

### 1. Email Analysis

- Language detection  
- Urgency estimation  
- Sentiment analysis  
- Category classification  
- Summary generation  
- Action items extraction  

### 2. AI-Generated Replies

Configurable tone, formality, length, and number of reply options.  
Each reply contains a suggested subject + a ready-to-send email body.

---

## 📥 Gmail Integration (Local Only)

Local-only Gmail features:

- OAuth login  
- Inbox messages preview  
- Load full email body  
- Full AI processing pipeline  

Gmail integration is read‑only and meant for portfolio/demo use.

---

## 🛠 Tech Stack

- Python  
- Streamlit  
- OpenAI API  
- Gmail API  
- python-dotenv  
- google-api-python-client  

---

## 🚀 Getting Started (Manual Mode)

Clone the repo and run:

```
pip install -r requirements.txt
streamlit run app.py
```

Add your `.env`:

```
OPENAI_API_KEY=sk-xxxxx
```

---

## 📧 Enabling Gmail Mode (Local Only)

1. Create a Google Cloud project  
2. Enable Gmail API  
3. Configure OAuth consent screen  
4. Create OAuth Desktop credentials  
5. Place `credentials.json` in project root  
6. Run `streamlit run app.py` and choose Gmail mode  

---

## 🌐 Why Gmail Mode Cannot Run in Public Deploy

Google requires domain verification + production OAuth, which Streamlit Cloud cannot provide.

Thus:

- Local app → Gmail mode ON  
- Public demo → manual mode only  

---

## 🧭 Roadmap

- Rewrite-my-draft mode  
- Style presets  
- Model quality toggle  
- Export formats  
- Slack / Notion automations  

---

## 👤 Author

Davide Tonello  
AI Automation Engineer

