# config.py

import os
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SLACK_USER_TOKEN = os.environ.get("SLACK_USER_TOKEN")
SLACK_CLIENT_ID = os.environ.get("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.environ.get("SLACK_CLIENT_SECRET")

LOCAL_LLM = os.environ.get("LOCAL_LLM", "False") == "True"
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB = os.environ.get("MONGODB_DB")

JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
JIRA_USERNAME = os.environ.get("JIRA_USERNAME")
JIRA_INSTANCE_URL = os.environ.get("JIRA_INSTANCE_URL")
