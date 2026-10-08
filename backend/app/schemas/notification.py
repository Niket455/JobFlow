from pydantic import BaseModel


class TestEmailResult(BaseModel):
    sent: bool
    to: str
    provider: str
