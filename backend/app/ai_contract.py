from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class StructuredOutputError(Exception):
    pass


class RenameColumnOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["rename_column"]
    column_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)


class CreateCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["create_card"]
    column_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(max_length=4000)


class UpdateCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["update_card"]
    card_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(max_length=4000)


class MoveCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["move_card"]
    card_id: str = Field(min_length=1)
    column_id: str = Field(min_length=1)
    position: int = Field(ge=0)


class DeleteCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["delete_card"]
    card_id: str = Field(min_length=1)


BoardOperation = Annotated[
    RenameColumnOperation
    | CreateCardOperation
    | UpdateCardOperation
    | MoveCardOperation
    | DeleteCardOperation,
    Field(discriminator="type"),
]


class AiChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["1"]
    response: str = Field(min_length=1, max_length=4000)
    operations: list[BoardOperation]


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


def parse_ai_response(content: str) -> AiChatResponse:
    try:
        return AiChatResponse.model_validate_json(content)
    except ValidationError as error:
        raise StructuredOutputError("OpenRouter returned an invalid structured response.") from error


def response_schema() -> dict[str, object]:
    return AiChatResponse.model_json_schema()


def operation_to_dict(operation: BoardOperation) -> dict[str, object]:
    return TypeAdapter(BoardOperation).dump_python(operation)