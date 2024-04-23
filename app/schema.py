from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class JiraMetadata(BaseModel):
    organization_id: str


class UserSchema(BaseModel):
    user_id: str = Field(..., alias="_id")
    slack_user_id: str
    name: str
    metadata: Optional[Dict[str, Any]] = {}


class MessageSchema(BaseModel):
    message_id: str = Field(..., alias="_id")
    user_id: str
    content: str
    timestamp: str
    attachments: Optional[List[str]] = []


class ChannelSchema(BaseModel):
    channel_id: str = Field(..., alias="_id")
    name: str
    description: Optional[str]
    project_id: Optional[str]


class ProjectSchema(BaseModel):
    project_id: str = Field(..., alias="_id")
    name: str
    description: Optional[str]
    channel_ids: Optional[List[str]]
    context: Optional[str]


class ThreadStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"


class ThreadSchema(BaseModel):
    thread_id: str = Field(..., alias="_id")
    channel_id: str
    messages: List[str]
    status: ThreadStatus
