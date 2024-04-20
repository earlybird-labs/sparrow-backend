import logging

from .blocks.index import bug_form
from .config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
from .llm import llm_response
from .handlers import handle_open_modal

from slack_bolt import App


app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)


# Listen for a shortcut invocation
@app.action("open_modal")
def open_modal(ack, body, client):
    handle_open_modal(ack, body, client)


@app.event("app_mention")
def respond_to_mention(event, say):
    try:
        # Post a message in response to the app mention
        message = event["text"]
        print(message)
        response = llm_response(message)

        if response.bug:
            say(text=response.text, blocks=bug_form)
        else:
            say(text=response.text)

    except Exception as e:
        logging.error(f"Error responding to app mention: {e}")


if __name__ == "__main__":
    app.start(port=8000)
