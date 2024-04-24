from typing import List, Optional
from pydantic import BaseModel, Field
import enum


class RequestType(enum.Enum):
    feature_request = "feature_request"
    bug_report = "bug_report"
    general_request = "general_request"
    ai_conversation = "ai_conversation"
    conversation = "conversation"


class AIResponse(BaseModel):
    ai_response: str = Field(
        description="The assistant's response to the user's message.",
    )
