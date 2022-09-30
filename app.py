import json
import struct

import lmdb
from flask_lambda import FlaskLambda
# from flask import Flask
from flask import request

app = FlaskLambda(__name__)
# app = Flask(__name__)

config = json.load("config.json")

env = lmdb.open("/mnt/persist/db", max_dbs=10, map_size=200*1024*1024*1024)
accounts_db = env.open_db('accounts', create=True)


# Following https://gist.github.com/questjay/3f858c2fea1731d29ea20cd5cb444e30#file-flask-server-proxy
def serveProxied(upstreamPath):
    def generate():
        for chunk in r.raw.stream(decode_content=False):
            yield chunk
    return app.response_class(generate(), headers={k: v for k, v in request.headers.items() if k != 'x-account-id'})


@app.route('/proxy/<path:p>', methods=['GET', 'POST'])
def proxy_handler(p):
    account = request.headers['x-account-id']  # TODO: If the header is missing
    for k, v in config['costs'].items():
        if p.startsWith(k):
            with accounts_db.begin(write=True) as txn:
                remainder = txn.get(accounts_db, account)  # FIXME
                remainder = struct.unpack('Xf', remainder)  # float
                if v <= remainder:
                    txn.set(accounts_db, account, struct.pack('Xf', remainder - v))
                    return serveProxied(p)
            break


if __name__ == '__main__':
    app.run(debug=True)