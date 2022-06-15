from flask import Flask, jsonify
from config import API_HOST, API_PORT
import json


app = Flask(__name__)


@app.route('/bro_data', methods=['GET'])
def bro_data():
    data = get_json()
    return jsonify(data)


def get_json(path='./data.json'):
    with open(path, 'r') as f:
        data = json.load(f)
        return data


if __name__ == '__main__':
    app.run(host=API_HOST, port=API_PORT)