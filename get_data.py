from config import NETWORKS
from dateutil import parser


import time
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
    start = time.time()
    tasks = [asyncio.ensure_future(get_delegations(session, network)),
             asyncio.ensure_future(get_asset_price(session, network)),
             asyncio.ensure_future(get_asset_apr(session, network))]
    data = await asyncio.gather(*tasks)
    stop = time.time()
    print(network['name'], stop - start)
    if network['name'] == 'bostrom':
        denom = network['base_denom']
    else:
        denom = network['base_denom'][1:]
    info = {
        "network": network['name'],
        "apr": data[2][network['name']],
        "tokens": data[0][0],
        "delegators": len(data[0][1]),
        "denom": denom
    }
    data[2] = info
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
        try:
            resp = await resp.json()
            return {"price": float(resp[network['coingecko_api']]['usd'])}
        except Exception:
            return {"price": 0.0}


async def get_asset_apr(session, network):
    tasks = [asyncio.ensure_future(get_annual_provisions(session, network)),
             asyncio.ensure_future(get_bonded_tokens(session, network)),
             asyncio.ensure_future(get_community_tax(session, network)),
             asyncio.ensure_future(get_blocks_per_year(session, network)),
             asyncio.ensure_future(get_real_blocks_per_year(session, network))]
    data = await asyncio.gather(*tasks)
    if data[3] != 1.0:
        annual_coeff = data[4] / data[3]
    else:
        annual_coeff = 1.0
    apr = (data[0] / data[1]) * (1 - data[2]) * annual_coeff
    return {network['name']: apr}


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


async def get_annual_provisions(session, network):
    if network['name'] in ['bostrom', 'juno', 'microtick', 'gravity']:
        try:
            url = f"{network['lcd_api']}/cosmos/mint/v1beta1/annual_provisions"
            async with session.get(url) as resp:
                resp = await resp.json()
                return int(float(resp['annual_provisions']))
        except Exception:
            url = f"{network['lcd_api']}/minting/annual-provisions"
            async with session.get(url) as resp:
                resp = await resp.json()
                return int(float(resp['result']))
    elif network['name'] == 'stargaze':
        url = f"{network['lcd_api']}/minting/annual-provisions"
        async with session.get(url) as resp:
            resp = await resp.json()
            return int(float(resp['result']) * 0.50)
    elif network['name'] == 'osmosis':
        url = f"{network['lcd_api']}/osmosis/mint/v1beta1/epoch_provisions"
        async with session.get(url) as resp:
            resp = await resp.json()
            return int(float(resp['epoch_provisions']) * 365.3 * 0.25)
    elif network['name'] == 'evmos':
        url = f"{network['lcd_api']}/evmos/inflation/v1/epoch_mint_provision"
        async with session.get(url) as resp:
            resp = await resp.json()
            return int(float(resp['epoch_mint_provision']['amount']) * 365.3 * 0.533333334)
    elif network['name'] == 'emoney':
        supply = await get_supply(session, network)
        return int(supply * 0.10)
    elif network['name'] == 'crescent':
        url = "https://apigw-v2.crescent.network/params"
        async with session.get(url) as resp:
            resp = await resp.json()
            data = resp['data']
            annual_provisions_raw = [x for x in data if x['key'] == 'liquidstaking.total_reward_ucre_amount_per_year'][0]
            return int(annual_provisions_raw['value'])
    else:
        return 0


async def get_community_tax(session, network):
    url = f"{network['lcd_api']}/cosmos/distribution/v1beta1/params"
    if network['name'] == 'crescent':
        return 0.0
    else:
        try:
            async with session.get(url) as resp:
                resp = await resp.json()
                return float(resp['params']['community_tax'])
        except Exception as e:
            print(network['name'], e)
            return 0.0


async def get_blocks_per_year(session, network):
    try:
        url = f"{network['lcd_api']}/cosmos/mint/v1beta1/params"
        async with session.get(url) as resp:
            resp = await resp.json()
            try:
                return int(resp['params']['blocks_per_year'])
            except Exception as e:
                url = f"{network['lcd_api']}/minting/parameters"
                async with session.get(url) as resp:
                    resp = await resp.json()
                    return int(resp['result']['blocks_per_year'])
    except Exception:
        return 1.0


async def get_real_blocks_per_year(session, network):
    try:
        current_height, current_time = await get_block_info(session, network, 'latest')
        height = current_height - 100_000
        old_height, old_time = await get_block_info(session, network, height)
        current_time_unix = int(parser.parse(current_time).timestamp())
        old_time_unix = int(parser.parse(old_time).timestamp())
        diff = current_time_unix - old_time_unix
        real_block_time = diff / 100_000
        return int(31_561_920 / real_block_time)
    except Exception:
        return 1.0


async def get_block_info(session, network, height):
    try:
        url = f"{network['lcd_api']}/cosmos/base/tendermint/v1beta1/blocks/{height}"
        async with session.get(url) as resp:
            resp = await resp.json()
            height = int(resp['block']['header']['height'])
            timestamp = resp['block']['header']['time']
            return height, timestamp
    except Exception:
        url = f"{network['lcd_api']}/blocks/{height}"
        async with session.get(url) as resp:
            resp = await resp.json()
            height = int(resp['block']['header']['height'])
            timestamp = resp['block']['header']['time']
            return height, timestamp


async def get_data():
    networks_amount = get_networks(NETWORKS)
    prices = get_usd_prices()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for network in NETWORKS:
            tasks.append(asyncio.ensure_future(get_network_data(session, network)))
        networks = await asyncio.gather(*tasks)
        infos = []
        agents = []
        tokens_in_usd = 0
        tokens_in_atom = 0
        tokens_in_eth = 0
        tokens_in_btc = 0
        for network in networks:
            agents.extend(network[0][1])
            tokens_in_usd += network[0][0] * network[1]['price']
            _tokens_in_usd = network[0][0] * network[1]['price']
            tokens_in_atom += _tokens_in_usd / prices[0]
            tokens_in_eth += _tokens_in_usd / prices[1]
            tokens_in_btc += _tokens_in_usd / prices[2]
            infos.append(network[2])
        agents = len(list(dict.fromkeys(agents)))
        data = {
            "networks_validated": networks_amount,
            "delegators": agents,
            "tokens_in_usd": tokens_in_usd,
            "tokens_in_atom": tokens_in_atom,
            "tokens_in_eth": tokens_in_eth,
            "tokens_in_btc": tokens_in_btc,
            "infos": infos
        }
        with open('./data.json', 'w') as f:
            json.dump(data, f)


asyncio.run(get_data())
