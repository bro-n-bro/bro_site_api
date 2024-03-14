from datetime import datetime
from pydantic import BaseModel


class NetworkBase(BaseModel):
    apr: float
    delegators: int
    denom: str
    network: str
    place: int
    price: float
    tokens: int


class NetworkCreate(NetworkBase):
    pass


class Network(NetworkBase):
    id: int
    timestamp: datetime
    health: int

    class Config:
        orm_mode = True
