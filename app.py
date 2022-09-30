import json
import re
import struct

import lmdb
import requests as requests
from flask_compress import Compress
from flask_lambda import FlaskLambda
# from flask import Flask
from flask import request

app = FlaskLambda(__name__)
# app = Flask(__name__)
Compress(app)

with open("config.json") as config_file:
    config = json.load(config_file)

env = lmdb.open(f"{config['statePath']}", max_dbs=10, map_size=200*1024*1024*1024)
accounts_db = env.open_db(b'accounts', create=True)


# Following https://gist.github.com/questjay/3f858c2fea1731d29ea20cd5cb444e30#file-flask-server-proxy
def serve_proxied(upstream_path):
    request_headers = dict(request.headers)
    filter_request_headers(request_headers)
    r = make_request(config['upstreamPrefix'] + upstream_path, request.method, params={'key': config['upstreamKey']},
                     headers=request_headers, data=request.get_data())
    response_headers = dict(r.raw.headers)
    filter_response_headers(response_headers)

    def generate():
        for chunk in r.iter_content(chunk_size=1024):
            yield chunk

    out = app.response_class(generate(), headers=response_headers)
    out.status_code = r.status_code
    return out  # (r.text, r.status_code, headers)


def filter_request_headers(headers):
    entries_to_remove = [k for k in headers.keys() if k.lower() in ['host', 'x-account-id']]
    for k in entries_to_remove:
        del headers[k]
    for k, v in config['upstreamHeaders'].items():
        headers[k] = v


def filter_response_headers(headers):
    # http://tools.ietf.org/html/rfc2616#section-13.5.1
    hop_by_hop = ['connection', 'keep-alive', 'te', 'trailers', 'transfer-encoding', 'upgrade',
                  'content-length', 'content-encoding']  # my addition - Victor Porton
    entries_to_remove = [k for k in headers.keys() if k.lower() in hop_by_hop]
    for k in entries_to_remove:
        del headers[k]

    # FIXME
    # accept only supported encodings
    # if 'Accept-Encoding' in headers:
    #     ae = headers['Accept-Encoding']
    #     filtered_encodings = [x for x in re.split(r',\s*', ae) if x in ('identity', 'gzip', 'x-gzip', 'deflate')]
    #     headers['Accept-Encoding'] = ', '.join(filtered_encodings)

    return headers


def make_request(url, method, headers={}, data=None, params=None):
    try:
        # LOG.debug("Sending %s %s with headers: %s and data %s", method, url, headers, data)
        print(url)
        return requests.request(method, url, params=params, stream=True,
                                headers=headers,
                                allow_redirects=False,
                                data=data)
    except Exception as e:
        print(e)


@app.route('/proxy/<path:p>', methods=['GET', 'POST'])
def proxy_handler(p):
    account = {k.lower(): v for k, v in request.headers.items()}['x-account-id']  # TODO: If the header is missing
    account = account.encode('utf-8')  # hack
    for k, v in config['costs'].items():
        if p.startswith(k):
            with env.begin(write=True) as txn:
                # remainder = txn.get(account)
                # if remainder is None:
                #     remainder = 0.0
                # else:
                #     remainder = struct.unpack('f', remainder)  # float
                remainder = 100000.0  # FIXME
                if v <= remainder:
                    txn.put(account, struct.pack('f', remainder - v))
                    upstream_path = re.sub(r"^/proxy/", "", request.full_path)
                    return serve_proxied(upstream_path)
            break
    return "Path not found."


if __name__ == '__main__':
    app.run(debug=True)