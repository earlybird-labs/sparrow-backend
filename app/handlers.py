import requests


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


def generate_response(prompt):
    """
    Generates a response from the Llama2 model for a given prompt.

    Args:
        prompt (str): The input prompt to generate a response for.

    Returns:
        str: The generated response from the model.
    """
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "dolphin", "prompt": prompt, "stream": False},
    )
    if response.status_code == 200:
        return response.json()["response"]
        # return "For sure"
    else:
        raise Exception(f"Failed to generate response: {response.text}")
