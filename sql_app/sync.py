import json

import requests
from cosmpy.aerial.client import LedgerClient
from sqlalchemy.orm import Session

from config import NETWORKS
from sql_app.models import Network
from sql_app.schemas import NetworkCreate

from cosmpy.protos.cosmos.base.query.v1beta1.pagination_pb2 import PageResponse, PageRequest
from cosmpy.protos.cosmos.staking.v1beta1.query_pb2 import QueryValidatorRequest, QueryValidatorsRequest, \
    QueryValidatorDelegationsRequest, QueryPoolRequest

from cosmpy.protos.cosmos.params.v1beta1.query_pb2 import QueryParamsRequest


def get_annual_provisions(network):
    if network['name'] not in ['stargaze', 'osmosis', 'evmos', 'emoney', 'crescent', 'stride']:
        try:
            url = f"{network['lcd_api']}/cosmos/mint/v1beta1/annual_provisions"
            resp = requests.get(url).json()
            return int(float(resp['annual_provisions']))
        except Exception:
            url = f"{network['lcd_api']}/minting/annual-provisions"
            resp = requests.get(url).json()
            return int(float(resp['result']))
    elif network['name'] == 'stargaze':
        url = f"{network['lcd_api']}/minting/annual-provisions"
        resp = requests.get(url).json()
        return int(float(resp['result']) * 0.4)
    elif network['name'] == 'osmosis':
        url = f"{network['lcd_api']}/osmosis/mint/v1beta1/epoch_provisions"
        resp = requests.get(url).json()
        return int(float(resp['epoch_provisions']) * 365.3 * 0.25)
    elif network['name'] == 'evmos':
        url = f"{network['lcd_api']}/evmos/inflation/v1/epoch_mint_provision"
        resp = requests.get(url).json()
        return int(float(resp['epoch_mint_provision']['amount']) * 365.3 * 0.533333334)
    elif network['name'] == 'stride':
        url = f"{network['lcd_api']}/mint/v1beta1/params"
        resp = requests.get(url).json()
        return float(resp['params']['genesis_epoch_provisions']) * \
               float(resp['params']['reduction_period_in_epochs']) * \
               float(resp['params']['distribution_proportions']['staking'])
    else:
        return 0


def get_apr(network, ledger_client):
    n = 500
    bonded_tokens_amount = int(ledger_client.staking.Pool(QueryPoolRequest()).pool.bonded_tokens)
    annual_provisions = get_annual_provisions(network)
    # if network['name'] == 'evmos':
    #     annual_provisions = float(requests.get(f"{network['lcd_api']}/evmos/inflation/v1/epoch_mint_provision").json()['epoch_mint_provision']['amount'])
    # else:
    #     annual_provisions = float(requests.get(f"{network['lcd_api']}/cosmos/mint/v1beta1/annual_provisions").json()['annual_provisions'])
    if network['name'] == 'empower':
        community_tax = 0.25
    elif network['name'] in ['composable', 'qwyon']:
        community_tax = 0.02
    else:
        req = QueryParamsRequest(subspace="distribution", key="communitytax")
        resp = ledger_client.params.Params(req)
        community_tax = float(json.loads(resp.param.value))
    # community_tax = float(json.loads(ledger_client.params.Params(QueryParamsRequest(subspace="distribution", key="communitytax")).param.value))
    current_height = ledger_client.query_height()
    current_height_time = ledger_client.query_block(current_height).time
    past_height_time = ledger_client.query_block(current_height - n).time
    diff = current_height_time - past_height_time
    try:
        real_block_time = diff.seconds / n
        real_blocks_per_year = 31561920 / real_block_time
        block_per_year = int(ledger_client.query_params(subspace='mint', key='BlocksPerYear'))
        correction_annual_coefficient = real_blocks_per_year / block_per_year
    except Exception as e:
        correction_annual_coefficient = 1
    return (annual_provisions * (1 - community_tax) / bonded_tokens_amount) * correction_annual_coefficient


def get_delegators_count(network, ledger_client):
    pagination = PageRequest(limit=500)
    delegators = 0
    while True:
        req = QueryValidatorDelegationsRequest(validator_addr=network['validator_addr'],
                                               pagination=pagination)
        res = ledger_client.staking.ValidatorDelegations(req)
        delegators += len(res.delegation_responses)
        if len(res.pagination.next_key) == 0:
            break
        pagination = PageRequest(limit=500, key=res.pagination.next_key)
    return delegators


def get_validators(ledger_client):
    pagination = PageRequest(limit=500)
    validators = []
    while True:
        req = QueryValidatorsRequest(pagination=pagination, status='BOND_STATUS_BONDED')
        res = ledger_client.staking.Validators(req)
        validators += res.validators
        if res.pagination.next_key:
            pagination = PageRequest(limit=500, key=res.pagination.next_key)
        else:
            break
    validators = sorted(validators, key=lambda validator: -int(validator.tokens))
    return validators


def sync_networks(db: Session):
    prices = requests.get('https://rpc.bronbro.io/price_feed_api/tokens/').json()
    for network in NETWORKS:
        try:
            print(network['name'])
            ledger_client = LedgerClient(network['cfg'])
            validators = get_validators(ledger_client)
            rank, validator = next(((i, validator) for i, validator in enumerate(validators) if
                                    validator.operator_address == network['validator_addr']), (-1, None))
            rank += 1
            tokens = int(validator.tokens) / 10 ** network['exponent']
            price = next((price['price'] for price in prices if price['symbol'] == network['symbol']), 0)
            apr = get_apr(network, ledger_client)

            network = {
                "apr": apr,
                "delegators": get_delegators_count(network, ledger_client),
                "denom": network['symbol'].lower(),
                "network": network['name'],
                "place": rank,
                "price": price,
                "tokens": tokens,
            }
            network = NetworkCreate.parse_obj(network)
            db_network = Network(**network.dict())
            db.add(db_network)
            db.commit()
        except Exception as e:
            print('aaaaa')
            print(e)

