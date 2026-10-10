from datetime import date

from pydantic import BaseModel, Field, model_validator


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    version_id: int | None = Field(default=None, ge=1)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeVersionMetadata(BaseModel):
    version: str = Field(min_length=1, max_length=50)
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "KnowledgeVersionMetadata":
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not be earlier than effective_from")
        return self
