from datetime import datetime
from typing import List, Any

import requests
from pydantic import BaseModel, ConfigDict, Extra, validator, Field
from pydantic_computed import Computed, computed


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
    networks_validated: Computed[int]
    delegators: Computed[int]
    tokens_in_atom: Computed[int]
    tokens_in_eth: Computed[int]
    tokens_in_btc: Computed[int]
    tokens_in_usd: Computed[int]

    @computed('networks_validated')
    def calculate_networks_validated(infos: List[Network], **kwargs) -> int:
        return len(infos)

    @computed('delegators')
    def calculate_delegators(infos: List[Network], **kwargs) -> int:
        return sum(item.delegators for item in infos)

    @computed('tokens_in_atom')
    def calculate_tokens_in_atom(infos: List[Network], **kwargs) -> int:
        prices = requests.get('https://rpc.bronbro.io/price_feed_api/tokens/').json()
        result = 0
        atom_price = next((item['price'] for item in prices if item['symbol'] == 'ATOM'), None)
        for network in infos:
            if network.price and atom_price:
                result += network.tokens * network.price / atom_price
        return result

    @computed('tokens_in_eth')
    def calculate_tokens_in_eth(infos: List[Network], **kwargs) -> int:
        prices = requests.get('https://rpc.bronbro.io/price_feed_api/tokens/').json()
        result = 0
        atom_price = next((item['price'] for item in prices if item['symbol'] == 'WETH.grv'), None)
        for network in infos:
            if network.price and atom_price:
                result += network.tokens * network.price / atom_price
        return result

    @computed('tokens_in_btc')
    def calculate_tokens_in_btc(infos: List[Network], **kwargs) -> int:
        prices = requests.get('https://rpc.bronbro.io/price_feed_api/tokens/').json()
        result = 0
        atom_price = next((item['price'] for item in prices if item['symbol'] == 'WBTC.axl'), None)
        for network in infos:
            if network.price and atom_price:
                result += network.tokens * network.price / atom_price
        return result


    @computed('tokens_in_usd')
    def calculate_tokens_in_usd(infos: List[Network], **kwargs) -> int:
        result = 0
        for network in infos:
            if network.price:
                result += network.tokens * network.price
        return result
