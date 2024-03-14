from cosmpy.aerial.config import NetworkConfig

NETWORKS = [
    {
        'cfg': NetworkConfig(
            chain_id="cosmoshub-4",
            url="<GRPC URL>",
            fee_minimum_gas_price=1,
            fee_denomination="uatom",
            staking_denomination="uatom",
        ),
        'lcd_api': '<LCD URL>',
        'validator_addr': '<VALIDATOR ADDRESS>',
        'symbol': 'ATOM',
        'name': 'cosmoshub',
        'exponent': 6
    },
    {
        'cfg': NetworkConfig(
            chain_id="evmos_9001-2",
            url="<GRPC URL>",
            fee_minimum_gas_price=1,
            fee_denomination="aevmos",
            staking_denomination="aevmos",
        ),
        'lcd_api': '<LCD URL>',
        'validator_addr': '<VALIDATOR ADDRESS>',
        'symbol': 'EVMOS',
        'name': 'evmos',
        'exponent': 18
    },
]
