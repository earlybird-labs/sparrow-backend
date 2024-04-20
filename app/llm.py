from simple_lm import SimpleLM
from instructor import Mode

from .config import TOGETHER_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
from .models import AIResponse
from .prompts import sparrow_system_prompt
from .utils import get_file_data

from openai import OpenAI
from anthropic import Anthropic

openai_client = OpenAI(api_key=OPENAI_API_KEY)
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)


simple_lm = SimpleLM()
simple_lm.setup_client(client_name="openai", api_key=OPENAI_API_KEY)
simple_lm.setup_client(
    client_name="together",
    api_key=TOGETHER_API_KEY,
)

simple_lm.set_model("openai", "gpt-4-turbo")
simple_lm.set_model("together", "meta-llama/Llama-3-70b-chat-hf")
simple_lm.set_model("ollama", "dolphin")


def transcribe_audio(file_url):
    audio_file = get_file_data(file_url)
    transcription = openai_client.audio.transcriptions.create(
        model="whisper-1", file=audio_file
    )
    return transcription.text


def create_speech(text):
    speech_file_path = "speech.mp3"
    response = openai_client.audio.speech.create(
        model="tts-1", voice="alloy", input=text
    )

    with open(speech_file_path, "wb") as file:
        file.write(response.content)


def describe_vision_anthropic(file_url, image_media_type, message=None):
    if message:
        prompt = message
    else:
        prompt = "Describe this image in as much detail as possible. Extract as much information as possible from the image."

    image_data = get_file_data(file_url)
    message = anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )
    return message.content[0].text


def describe_image(file_url):

    response = openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image."},
                    {
                        "type": "image_url",
                        "image_url": {"url": file_url},
                    },
                ],
            }
        ],
        max_tokens=1000,
    )

    return response.choices[0].message.content


def llm_response(messages, client_name="openai"):

    client = simple_lm.get_client(client_name)
    model = simple_lm.get_model(client_name)

    messages = [
        {"role": "system", "content": sparrow_system_prompt},
        *messages,
    ]

    response = client.create(
        model=model,
        messages=messages,
        response_model=AIResponse,
    )
    return response


if __name__ == "__main__":
    print(
        describe_vision_anthropic(
            file_url="https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
            image_media_type="image/jpeg",
        )
    )
