from typing import List, Optional
from pydantic import BaseModel, Field


class AIResponse(BaseModel):
    ai_response: str = Field(
        default="",
        description="The assistant's response to the user's message.",
    )
    bug: bool = Field(
        default=False,
        description="Whether the users message indicates they are having a bug.",
    )
