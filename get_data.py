from config import NETWORKS

import aiohttp
import asyncio
import requests
import json
from cyberpy._wallet import address_to_address


def get_networks(networks: list) -> int:
    return len(networks)


def get_usd_prices() -> tuple:
    atom = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=cosmos&vs_currencies=usd").json()['cosmos']['usd']
    eth = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()['ethereum']['usd']
    btc = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd").json()['bitcoin']['usd']
    return atom, eth, btc


async def get_network_data(session, network):
    tasks = [asyncio.ensure_future(get_delegations(session, network)),
             asyncio.ensure_future(get_asset_price(session, network)),
             asyncio.ensure_future(get_asset_apr(session, network))]
    data = await asyncio.gather(*tasks)
    return data


async def get_delegations(session, network):
    url = f"{network['lcd_api']}/staking/validators/{network['validator']}/delegations?limit=1000000"
    async with session.get(url) as resp:
        resp = await resp.json()
        delegations = resp['result']
        tokens = sum([int(d['balance']['amount']) for d in delegations]) / network['exponent']
        delegators = [address_to_address(d['delegation']['delegator_address'], 'prefix') for d in delegations]
        return tokens, delegators


async def get_asset_price(session, network):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={network['coingecko_api']}&vs_currencies=usd"
    async with session.get(url) as resp:
        resp = await resp.json()
        return {"price": float(resp[network['coingecko_api']]['usd'])}


async def get_asset_apr(session, network):
    tasks = [asyncio.ensure_future(get_inflation(session, network)),
             asyncio.ensure_future(get_bonded_tokens(session, network)),
             asyncio.ensure_future(get_supply(session, network))]
    try:
        data = await asyncio.gather(*tasks)
        return {network['name']: data[2] * data[0] / data[1]}
    except Exception:
        return {network['name']: 0}


async def get_inflation(session, network):
    url = f"{network['lcd_api']}/cosmos/mint/v1beta1/inflation"
    async with session.get(url) as resp:
        resp = await resp.json()
        return float(resp['inflation'])


async def get_bonded_tokens(session, network):
    url = f"{network['lcd_api']}/cosmos/staking/v1beta1/pool"
    async with session.get(url) as resp:
        resp = await resp.json()
        return int(resp['pool']['bonded_tokens'])


async def get_supply(session, network):
    url = f"{network['lcd_api']}/cosmos/bank/v1beta1/supply/{network['base_denom']}"
    async with session.get(url) as resp:
        resp = await resp.json()
        return int(resp['amount']['amount'])


async def get_data():
    networks_amount = get_networks(NETWORKS)
    prices = get_usd_prices()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for network in NETWORKS:
            tasks.append(asyncio.ensure_future(get_network_data(session, network)))
        networks = await asyncio.gather(*tasks)
        aprs = []
        agents = []
        tokens_in_usd = 0
        tokens_in_atom = 0
        tokens_in_eth = 0
        tokens_in_btc = 0
        for network in networks:
            agents.extend(network[0][1])
            tokens_in_usd += network[0][0] * network[1]['price']
            tokens_in_atom += tokens_in_usd / prices[0]
            tokens_in_eth += tokens_in_usd / prices[1]
            tokens_in_btc += tokens_in_usd / prices[2]
            aprs.append(network[2])
        agents = len(list(dict.fromkeys(agents)))
        data = {
            "networks_validated": networks_amount,
            "delegators": agents,
            "tokens_in_usd": tokens_in_usd,
            "tokens_in_atom": tokens_in_atom,
            "tokens_in_eth": tokens_in_eth,
            "tokens_in_btc": tokens_in_btc,
            "aprs": aprs
        }
        with open('./data.json', 'w') as f:
            json.dump(data, f)


asyncio.run(get_data())
