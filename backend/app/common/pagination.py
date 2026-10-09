from pydantic import BaseModel, Field, field_validator


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str | None = None
    sort_order: str = "desc"

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, value: str) -> str:
        if value not in {"asc", "desc"}:
            raise ValueError("sort_order must be asc or desc")
        return value

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
