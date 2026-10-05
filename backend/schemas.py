from pydantic import BaseModel


class Horizon(BaseModel):
    name: str = "1d"
    hours: int = 24


class FYPRequest(BaseModel):
    request_id: str
    location: str = "Gujarat"
    horizon: Horizon