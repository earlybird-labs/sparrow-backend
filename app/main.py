import os

from slack_bolt import App

from .config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

from .handlers import (
    handle_message,
    handle_onboard,
    handle_onboarding_modal_open,
    handle_onboarding_modal_submit,
    handle_sparrow,
    handle_reaction_added,
    handle_url_verification,
    handle_create_jira_yes,
    handle_create_jira_no,
)

app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)

# Event handlers
app.event("url_verification")(handle_url_verification)
app.event("message")(handle_message)
app.event("reaction_added")(handle_reaction_added)

# Command handlers
app.command("/onboard")(handle_onboard)
app.command("/sparrow")(handle_sparrow)

# Action handlers
app.action("start_onboarding")(handle_onboarding_modal_open)
app.action("create_jira_yes")(handle_create_jira_yes)
app.action("create_jira_no")(handle_create_jira_no)

# View handlers
app.view("onboarding_modal")(handle_onboarding_modal_submit)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"Starting app on port {port}")
    app.start(port=port)
