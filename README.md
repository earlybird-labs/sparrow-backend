# Sparrow Slack Bot

This Slack bot is designed to assist users in a Slack workspace by responding to messages, opening modals for input, and handling bug reports. It leverages the Slack Bolt framework for Python and integrates with language models for generating responses.

## Features

- **Message Handling**: Responds to direct messages and messages in threads, including those with file attachments.
- **Modal Interaction**: Opens modals for user input and handles submissions.
- **AI Integration**: Utilizes language models for generating conversational responses and processing images and audio files.

## Setup Instructions

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/earlybird-labs/sparrow-backend.git
    cd sparrow-backend
    ```

2. **Create a Virtual Environment**:
    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

3. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure Environment Variables**: Populate a `.env` file with necessary keys.
    ```plaintext
    SLACK_BOT_TOKEN=your_slack_bot_token
    SLACK_SIGNING_SECRET=your_slack_signing_secret
    TOGETHER_API_KEY=your_together_api_key
    OPENAI_API_KEY=your_openai_api_key
    ANTHROPIC_API_KEY=your_anthropic_api_key
    ```

5. **Run the Bot**:
    ```bash
    python -m app.main
    ```

## Usage

- **Responding to Direct Messages**: Handles direct messages, including those with file attachments.
- **Responding to Thread Messages**: Handles messages in threads, including those with file attachments.
- **Opening and Handling Modals**: Opens modals for user input and processes the input upon submission.

## Code Highlights

- **AI Response Generation**: Generates responses using language models. See `app/llm.py`.
- **File Handling**: Processes file attachments in messages, including image and audio files. See `app/handlers.py`.
- **Modal Handling**: Opens modals and handles submissions. See `app/handlers.py`.

## Contributing

Contributions are welcome. Please maintain clean, efficient, and well-commented code.

## License

[Apache 2.0](LICENSE)

