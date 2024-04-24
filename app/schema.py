# schema.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Annotated, Any, Callable

from enum import Enum

from bson import ObjectId


from pydantic import BaseModel, ConfigDict, Field, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class _ObjectIdPydanticAnnotation:
    # Based on https://docs.pydantic.dev/latest/usage/types/custom/#handling-third-party-types.

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_from_str(input_value: str) -> ObjectId:
            return ObjectId(input_value)

        return core_schema.union_schema(
            [
                # check if it's an instance first before doing any further work
                core_schema.is_instance_schema(ObjectId),
                core_schema.no_info_plain_validator_function(validate_from_str),
            ],
            serialization=core_schema.to_string_ser_schema(),
        )


PydanticObjectId = Annotated[ObjectId, _ObjectIdPydanticAnnotation]


class JiraMetadata(BaseModel):
    organization_id: str


class UserSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: PydanticObjectId = Field(alias="_id")
    slack_user_id: str
    name: str
    email: str
    metadata: Optional[Dict[str, Any]] = {}


class MessageSchema(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    user_id: str
    content: str
    timestamp: str
    attachments: Optional[List[str]] = []


class ChannelSchema(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    name: str
    description: Optional[str]
    project_id: Optional[str]


class ProjectSchema(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    name: str
    description: Optional[str]
    channel_ids: Optional[List[str]]
    context: Optional[str]


class ThreadStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"


class ThreadSchema(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    channel_id: str
    ts: str
    status: Optional[ThreadStatus] = ThreadStatus.OPEN
