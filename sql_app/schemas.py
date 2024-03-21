from datetime import datetime
from typing import List

import requests
from pydantic import BaseModel, computed_field, ConfigDict, Extra


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


class FullInfo(BaseModel):
    infos: List[Network]

    @property
    def prices(self) -> List[dict]:
        return requests.get('https://rpc.bronbro.io/price_feed_api/tokens/').json()

    @computed_field
    @property
    def networks_validated(self) -> int:
        return len(self.infos)

    @computed_field
    @property
    def delegators(self) -> int:
        return sum(item.delegators for item in self.infos)

    @computed_field
    @property
    def tokens_in_atom(self) -> int:
        result = 0
        atom_price = next((item['price'] for item in self.prices if item['symbol'] == 'ATOM'), None)
        for network in self.infos:
            if network.price and atom_price:
                result += network.tokens * network.price / atom_price
        return result

    @computed_field
    @property
    def tokens_in_eth(self) -> int:
        result = 0
        atom_price = next((item['price'] for item in self.prices if item['symbol'] == 'WETH.grv'), None)
        for network in self.infos:
            if network.price and atom_price:
                result += network.tokens * network.price / atom_price
        return result

    @computed_field
    @property
    def tokens_in_btc(self) -> int:
        result = 0
        atom_price = next((item['price'] for item in self.prices if item['symbol'] == 'WBTC.axl'), None)
        for network in self.infos:
            if network.price and atom_price:
                result += network.tokens * network.price / atom_price
        return result

    @computed_field
    @property
    def tokens_in_usd(self) -> int:
        result = 0
        for network in self.infos:
            if network.price:
                result += network.tokens * network.price
        return result
