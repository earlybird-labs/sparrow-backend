import os
from dotenv import load_dotenv

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from pydantic import BaseModel

import uvicorn

from .models import SlackCommand, SparrowResponse, SlackEvent, SlackEventCallback
from .prompts import sparrow_system_prompt
from .utils import extract_plain_text_from_blocks

from simple_lm import SimpleLM
from slack_bolt import App


load_dotenv()


# app = FastAPI()

# Initialize your app with your bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

lm = SimpleLM()

together = lm.setup_client(
    client_name="together",
    api_key=os.getenv("TOGETHER_API_KEY"),
)

ollama = lm.setup_client(client_name="ollama", api_key="null")


def lm_response(user_message):
    response = together.create(
        model="meta-llama/Llama-3-70b-chat-hf",
        messages=[
            {"role": "system", "content": sparrow_system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_model=SparrowResponse,
    )
    return response.text


# Listen for a shortcut invocation
@app.action("open_modal")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()
    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            # View identifier
            "callback_id": "view_1",
            "title": {"type": "plain_text", "text": "Sparrow"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "input_c",
                    "label": {
                        "type": "plain_text",
                        "text": "What are your hopes and dreams?",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "dreamy_input",
                        "multiline": True,
                    },
                },
            ],
        },
    )


@app.event("app_mention")
def respond_to_mention(event, say):
    try:
        # Post a message in response to the app mention
        message = event["text"]
        print(message)
        response = lm_response(message)
        say(
            text=response,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": response,
                    },
                },
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Click Me"},
                            "action_id": "open_modal",
                        }
                    ],
                },
            ],
        )

    except Exception as e:
        logging.error(f"Error responding to app mention: {e}")


if __name__ == "__main__":
    app.start(port=8000)
