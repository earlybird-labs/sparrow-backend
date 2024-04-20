import logging

from .blocks.index import bug_form
from .config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
from .llm import llm_response
from .handlers import handle_open_modal, generate_response
from .utils import safe_say


from slack_bolt import App


app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)


# Listen for a shortcut invocation
@app.action("open_modal")
def open_modal(ack, body, client):
    handle_open_modal(ack, body, client)


@app.event("message")
def handle_thread_messages(ack, client, message, say):
    # Acknowledge the event first
    ack()

    # Check if the message is in a thread by looking for thread_ts
    if message.get("thread_ts"):
        # Fetch the parent message of the thread
        parent_message = client.conversations_replies(
            channel=message["channel"], ts=message["thread_ts"], limit=1
        )

        bot_id = client.auth_test()["user_id"]
        first_message_text = parent_message["messages"][0]["text"]

        # Check if the bot is mentioned in the parent message text
        if f"<@{bot_id}>" in first_message_text:
            # Fetch all messages from the thread and convert them to the required format
            thread_messages = client.conversations_replies(
                channel=message["channel"], ts=message["thread_ts"]
            )["messages"]

            print(thread_messages)

            # Initialize an empty list to hold the formatted messages
            formatted_messages = []

            # Loop through each message in the thread
            for msg in thread_messages:
                # Determine the role based on the user who sent the message
                role = "assistant" if msg.get("user") == bot_id else "user"
                # Append the formatted message to the list
                formatted_messages.append({"role": role, "content": msg["text"]})

            print(formatted_messages)

            response = llm_response(formatted_messages)
            safe_say(say, text=response.ai_response, thread_ts=message["thread_ts"])


@app.event("app_mention")
def respond_to_mention(ack, event, say):
    ack()
    try:
        # Post a message in response to the app mention in a thread
        message = event["text"]
        user_message = {"role": "user", "content": message}
        response = llm_response([user_message])

        # Extract the timestamp of the original message to use as thread_ts
        thread_ts = event["ts"]

        if response.bug:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": response.ai_response,
                    },
                }
            ] + bug_form

            safe_say(
                say,
                text=response.ai_response,
                blocks=blocks,
                thread_ts=thread_ts,
            )
        else:
            safe_say(say, text=response.ai_response, thread_ts=thread_ts)

    except Exception as e:
        logging.error(f"Error responding to app mention: {e}")


if __name__ == "__main__":
    app.start(port=8000)
