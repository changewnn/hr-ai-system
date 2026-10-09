from datetime import datetime

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None
    leader_id: int | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = None
    leader_id: int | None = None


class DepartmentNode(BaseModel):
    id: int
    name: str
    parent_id: int | None
    leader_id: int | None
    created_at: datetime
    children: list["DepartmentNode"] = Field(default_factory=list)


DepartmentNode.model_rebuild()
