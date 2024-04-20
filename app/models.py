from pydantic import BaseModel, Field


class Block(BaseModel):
    type: str


class Form(BaseModel):
    type: str
    block_id: str
    label: str
    element: str


class Button(BaseModel):
    text: str
    action_id: str


class AIResponse(BaseModel):
    text: str
    bug: bool = Field(
        default=False,
        description="Whether the users message indicates they are having a bug.",
    )


from typing import List, Optional
from pydantic import BaseModel, Field


class Authorization(BaseModel):
    enterprise_id: Optional[str] = None
    team_id: str
    user_id: str
    is_bot: bool
    is_enterprise_install: bool


class SlackEvent(BaseModel):
    user: str
    type: str
    ts: str
    client_msg_id: str
    text: str
    team: str
    blocks: List[dict]
    channel: str
    event_ts: str


class SlackEventCallback(BaseModel):
    token: str = Field(
        ..., description="Verification token to validate the source of the event."
    )
    team_id: str = Field(
        ..., description="The unique identifier for the team where the event occurred."
    )
    api_app_id: str = Field(
        ..., description="The unique identifier for the app that is handling the event."
    )
    event: SlackEvent = Field(
        ..., description="The event data containing the specific event details."
    )
    type: str = Field(
        default="event_callback",
        description="The type of event. Defaults to 'event_callback'.",
    )
    event_id: str = Field(
        ..., description="A unique identifier for this specific event."
    )
    event_time: int = Field(
        ..., description="The timestamp of when the event occurred."
    )
    authorizations: List[Authorization] = Field(
        ..., description="Information about the authorizations related to this event."
    )
    is_ext_shared_channel: bool = Field(
        ..., description="Indicates if the event is from an external shared channel."
    )
    event_context: str = Field(
        ..., description="A string that provides context about the event."
    )


class SlackCommand(BaseModel):
    token: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    api_app_id: str
    is_enterprise_install: str
    response_url: str
    trigger_id: str
