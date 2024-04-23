from typing import List, Optional
from pydantic import BaseModel, Field
import enum


class RequestType(enum.Enum):
    feature_request = "feature_request"
    bug_report = "bug_report"
    general_request = "general_request"
    conversation = "conversation"


class AIResponse(BaseModel):
    ai_response: str = Field(
        default="",
        description="The assistant's response to the user's message.",
    )
    request_type: Optional[RequestType] = Field(
        default=None,
        description="The type of request the user is making.",
    )
