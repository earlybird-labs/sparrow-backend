# main.py

import os
from slack_bolt import App
from .config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
from dotenv import load_dotenv

load_dotenv()

from .handlers.message_handler import MessageHandler
from .slack_api import SlackClient
from .llm import LLMClient
from .database import Database


app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
slack_client = SlackClient(app)
llm_client = LLMClient()
database = Database()
message_handler = MessageHandler(slack_client, llm_client, database)


@app.event("url_verification")
def handle_url_verification(ack, body):
    challenge = body.get("challenge")
    ack(challenge)


@app.event("message")
def handle_message(ack, client, event, message, say):
    message_handler.handle_message(ack, client, event, message, say)


@app.event("reaction_added")
def handle_reaction_added(ack, client, event):
    message_handler.handle_reaction_added(ack, client, event)


# Command handlers
@app.command("/sparrow")
def handle_sparrow(ack, client, respond, command):
    message_handler.handle_sparrow(ack, client, respond, command)


# Action handlers
@app.action("start_onboarding")
def handle_onboarding_modal_open(ack, body, client):
    message_handler.handle_onboarding_modal_open(ack, body, client)


@app.action("create_jira_yes")
def handle_create_jira_yes(ack, body, client, respond):
    message_handler.handle_create_jira_yes(ack, body, client, respond)


@app.action("create_jira_no")
def handle_create_jira_no(ack, body, client, say, respond):
    message_handler.handle_create_jira_no(ack, body, client, say, respond)


# View handlers
@app.view("onboarding_modal")
def handle_onboarding_modal_submit(ack, body, view):
    message_handler.handle_onboarding_modal_submit(ack, body, view)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"Starting app on port {port}")
    app.start(port=port)
