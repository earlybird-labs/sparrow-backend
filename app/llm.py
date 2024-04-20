from simple_lm import SimpleLM
from instructor import Mode

from .config import TOGETHER_API_KEY, OPENAI_API_KEY
from .models import AIResponse
from .prompts import sparrow_system_prompt


simple_lm = SimpleLM()

openai = simple_lm.setup_client(client_name="openai", api_key=OPENAI_API_KEY)

together = simple_lm.setup_client(
    client_name="together",
    api_key=TOGETHER_API_KEY,
)

ollama = simple_lm.setup_client(client_name="ollama", api_key="null", mode=Mode.MD_JSON)


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
