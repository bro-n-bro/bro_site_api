from config import NETWORKS
from dateutil import parser
from operator import itemgetter


import time
import aiohttp
import asyncio
from cyberpy._wallet import address_to_address
from db import set_value_by_network, set_value_by_api, create_table


async def get_usd_prices():
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            asyncio.ensure_future((get_asset_price(session, {"name": "cosmos", "coingecko_api": "cosmos"}))),
            asyncio.ensure_future((get_asset_price(session, {"name": "ethereum", "coingecko_api": "ethereum"}))),
            asyncio.ensure_future((get_asset_price(session, {"name": "bitcoin", "coingecko_api": "bitcoin"}))),
        ]
        prices = await asyncio.gather(*tasks)
        set_value_by_api('cosmos', 'price', prices[0]['price'])
        set_value_by_api('ethereum', 'price', prices[1]['price'])
        set_value_by_api('bitcoin', 'price', prices[2]['price'])


async def get_network_data(session, network):
    start = time.time()
    tasks = [asyncio.ensure_future(get_delegations(session, network)),
             asyncio.ensure_future(get_asset_price(session, network)),
             asyncio.ensure_future(get_asset_apr(session, network)),
             asyncio.ensure_future(get_network_set(session, network))]
    data = await asyncio.gather(*tasks)
    stop = time.time()
    print(network['name'], stop - start)
    halt_amount, fork_amount, vals = get_halt_fork(data[3])
    place = get_network_place(data[3], network['validator'])
    set_value_by_network(network['name'], 'place', place)
    health = get_network_health(halt_amount, fork_amount)
    set_value_by_network(network['name'], 'health', health)
    if network['name'] == 'bostrom':
        denom = network['base_denom']
    else:
        denom = network['base_denom'][1:]
    set_value_by_network(network['name'], 'denom', denom)


def get_network_health(halt_amount: int, fork_amount: int):
    return (halt_amount * fork_amount) ** 0.5


def get_halt_fork(validator_set: list):
    validator_set = [
        {
            "operator_address": v['operator_address'],
            "tokens": int(v['tokens'])
        } for v in validator_set if not v['jailed'] and v['status'] == 'BOND_STATUS_BONDED']
    validator_set = sorted(validator_set, key=itemgetter('tokens'), reverse=True)
    tokens = sum([int(v['tokens']) for v in validator_set])
    halt_amount = 0
    fork_amount = 0
    _tokens = 0
    for _ in validator_set:
        _tokens += _['tokens']
        if _tokens / tokens < 0.333333333:
            halt_amount += 1
        elif _tokens / tokens < 0.66666666:
            fork_amount += 1
        else:
            continue
    halt_amount += 1
    fork_amount += 1
    return halt_amount, fork_amount, len(validator_set)


def get_network_place(validator_set: list, validator: str):
    validator_set = [
        {
            "operator_address": v['operator_address'],
            "tokens": int(v['tokens'])
        } for v in validator_set if not v['jailed'] and v['status'] == 'BOND_STATUS_BONDED']
    validator_set = sorted(validator_set, key=itemgetter('tokens'), reverse=True)
    try:
        item = [v for v in validator_set if v['operator_address'] == validator][0]
        index = validator_set.index(item)
        return index + 1
    except IndexError as e:
        print(e)
        return 0


async def get_network_set(session, network):
    url = f"{network['lcd_api']}/cosmos/staking/v1beta1/validators?pagination.limit=10000"
    async with session.get(url) as resp:
        resp = await resp.json()
        validators_set = resp['validators']
        return validators_set


async def get_delegations(session, network):
    url = f"{network['lcd_api']}/cosmos/staking/v1beta1/validators/{network['validator']}/delegations?pagination.limit=100000"
    async with session.get(url) as resp:
        resp = await resp.json()
        delegations = resp['delegation_responses']
        tokens = sum([int(d['balance']['amount']) for d in delegations]) / network['exponent']
        delegators = [address_to_address(d['delegation']['delegator_address'], 'prefix') for d in delegations]
        set_value_by_network(network['name'], 'delegators', len(delegators))
        set_value_by_network(network['name'], 'tokens', tokens)
        return tokens, delegators


async def get_asset_price(session, network):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={network['coingecko_api']}&vs_currencies=usd"
    async with session.get(url) as resp:
        try:
            resp = await resp.json()
            set_value_by_network(network['name'], 'price', float(resp[network['coingecko_api']]['usd']))
            return {"price": float(resp[network['coingecko_api']]['usd'])}
        except Exception as e:
            print(e)
            pass


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
    set_value_by_network(network['name'], 'apr', apr)
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
    if network['name'] not in ['stargaze', 'osmosis', 'evmos', 'emoney', 'crescent', 'stride']:
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
    elif network['name'] == 'stride':
        url = f"{network['lcd_api']}/mint/v1beta1/params"
        async with session.get(url) as resp:
            resp = await resp.json()
            return float(resp['params']['genesis_epoch_provisions']) * \
                   float(resp['params']['reduction_period_in_epochs']) * \
                   float(resp['params']['distribution_proportions']['staking'])
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
        height = current_height - 1000
        old_height, old_time = await get_block_info(session, network, height)
        current_time_unix = int(parser.parse(current_time).timestamp())
        old_time_unix = int(parser.parse(old_time).timestamp())
        diff = current_time_unix - old_time_unix
        real_block_time = diff / 1000
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
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for network in NETWORKS:
            tasks.append(asyncio.ensure_future(get_network_data(session, network)))
        networks = await asyncio.gather(*tasks)


def main():
    create_table()
    asyncio.run(get_data())
    asyncio.run(get_usd_prices())


if __name__ == '__main__':
    main()

