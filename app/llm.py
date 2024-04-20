from simple_lm import SimpleLM
from instructor import Mode

from .config import TOGETHER_API_KEY
from .models import AIResponse
from .prompts import sparrow_system_prompt


simple_lm = SimpleLM()

together = simple_lm.setup_client(
    client_name="together",
    api_key=TOGETHER_API_KEY,
)

ollama = simple_lm.setup_client(client_name="ollama", api_key="null", mode=Mode.MD_JSON)


def llm_response(user_message):
    response = together.create(
        model="meta-llama/Llama-3-70b-chat-hf",
        messages=[
            {"role": "system", "content": sparrow_system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_model=AIResponse,
    )
    return response
