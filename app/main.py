import os

from slack_bolt import App

from .config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
from .handlers import (
    handle_message,
    handle_onboard,
    handle_onboarding_modal_open,
    handle_onboarding_modal_submit,
)

app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)


@app.event("url_verification")
def handle_url_verification(event_data):
    return event_data["challenge"]


app.event("message")(handle_message)
app.command("/onboard")(handle_onboard)
app.action("start_onboarding")(handle_onboarding_modal_open)
app.view("onboarding_modal")(handle_onboarding_modal_submit)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting app on port {port}")
    app.start(port=port)
