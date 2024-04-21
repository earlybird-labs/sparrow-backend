import os

from slack_bolt import App

from .blocks.index import bug_form
from .config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
from .llm import llm_response
from .handlers import (
    # handle_open_modal,
    handle_message,
    handle_command,
    # handle_app_mention,
    # handle_file_shared,
)

app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)


@app.event("url_verification")
def handle_url_verification(event_data):
    return event_data["challenge"]


# app.action("open_modal")(handle_open_modal)
app.event("message")(handle_message)
app.command("/sparrow")(handle_command)
# app.event("app_mention")(handle_app_mention)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting app on port {port}")
    app.start(port=port)
