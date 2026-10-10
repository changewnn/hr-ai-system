from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class AgentMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)
