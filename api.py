from flask import Flask, jsonify
from config import API_HOST, API_PORT
from db import get_all_rows, get_prices
import json


app = Flask(__name__)


@app.route('/bro_data', methods=['GET'])
def bro_data():
    data = get_all_rows()
    res = []
    for i in data:
        d = {
                "apr": i[1],
                "delegators": i[2],
                "denom": i[3],
                "health": i[4],
                "network": i[0],
                "place": i[5],
                "tokens": i[6],
                "price": i[7]
            }
        res.append(d)
    tokens_in_usd = sum([i[6] * i[7] for i in data if i[6] and i[7]])
    prices = get_prices()
    return jsonify({
        "infos": res,
        "delegators": sum([i[2] for i in data if i[2]]),
        "networks_validated": len(data),
        "tokens_in_usd": tokens_in_usd,
        "tokens_in_btc": tokens_in_usd / prices[2][1],
        "tokens_in_eth": tokens_in_usd / prices[1][1],
        "tokens_in_atom": tokens_in_usd / prices[0][1]
    })


if __name__ == '__main__':
    app.run(host=API_HOST, port=API_PORT)