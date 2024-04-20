# Slack Bot for Bug Reporting and Assistance

This Slack bot is designed to assist users in a Slack workspace by responding to messages, opening modals for input, and handling bug reports. It leverages the Slack Bolt framework for Python and integrates with language models for generating responses.

## Features

- **Message Handling**: Responds to messages in threads where the bot is mentioned.
- **Modal Interaction**: Opens a modal for user input upon specific actions.
- **Bug Reporting**: Provides a structured form for reporting bugs, including issue name, description, and urgency.
- **AI Integration**: Utilizes language models to generate conversational and helpful responses.

## Setup

1. **Requirements Installation**: Install the necessary Python packages from [requirements.txt](file:///Users/joepetrantoni/earlybird/sparrow-python/requirements.txt#1%2C1-1%2C1).

    ```bash
    pip install -r requirements.txt
    ```

2. **Environment Variables**: Set up the required environment variables in a `.env` file.

    ```plaintext
    SLACK_BOT_TOKEN=your_slack_bot_token
    SLACK_SIGNING_SECRET=your_slack_signing_secret
    TOGETHER_API_KEY=your_together_api_key
    OPENAI_API_KEY=your_openai_api_key
    ```

3. **Running the Bot**: Use the provided `Procfile` for deployment or run the bot locally.

    ```bash
    uvicorn app.main:app --host=0.0.0.0 --port=8000
    ```

## Usage

- **Responding to Mentions**: The bot responds to mentions in channels with helpful information or actions.
- **Opening Modals**: Triggered by specific actions (e.g., shortcuts), the bot can open modals for user input.
- **Bug Reporting**: Users can report bugs through a structured form that the bot provides in response to certain triggers.

## Code Highlights

- **Bug Form JSON**: The structure of the bug reporting form is defined in `app/blocks/bug_form.json`.
- **Event Handling**: The bot listens for messages and app mentions, handling them in `app/main.py`.

    
```25:62:app/main.py
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
```


    
```65:77:app/main.py
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

        safe_say(say, text=response.ai_response, thread_ts=thread_ts)
```


- **Modal Handling**: Modals are opened through actions defined in `app/handlers.py`.

    
```4:34:app/handlers.py
def handle_open_modal(ack, body, client):
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
```


- **AI Response Generation**: The bot generates responses using language models in `app/llm.py`.

    
```21:33:app/llm.py
def llm_response(messages):

    messages = [
        {"role": "system", "content": sparrow_system_prompt},
        *messages,
    ]

    response = openai.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        response_model=AIResponse,
    )
    return response
```


## Contributing

Contributions to improve the bot or add new features are welcome. Please follow the existing code structure and maintain clean, efficient, and well-commented code.

## License

[MIT License](https://choosealicense.com/licenses/mit/)

