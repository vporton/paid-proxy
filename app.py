import json
import struct

import lmdb
from flask_lambda import FlaskLambda
# from flask import Flask
from flask import request

app = FlaskLambda(__name__)
# app = Flask(__name__)

with open("config.json") as config_file:
    config = json.load(config_file)

env = lmdb.open(f"{config['statePath']}", max_dbs=10, map_size=200*1024*1024*1024)
accounts_db = env.open_db(b'accounts', create=True)


# Following https://gist.github.com/questjay/3f858c2fea1731d29ea20cd5cb444e30#file-flask-server-proxy
def serve_proxied(upstream_path):
    r = make_request(config['upstreamPrefix'] + upstream_path, request.method, dict(request.headers), request.form)
    print("RR", r)
    headers = dict(r.raw.headers)
    filter_headers(headers)

    def generate():
        for chunk in r.raw.stream(decode_content=False):
            yield chunk

    out = app.response_class(generate(), headers=headers)
    out.status_code = r.status_code
    return out  # (r.text, r.status_code, headers)


def filter_headers(headers):
    # http://tools.ietf.org/html/rfc2616#section-13.5.1
    hop_by_hop = ('Connection', 'Keep-Alive', 'Te', 'Trailers', 'Transfer-Encoding', 'Upgrade')
    for k in hop_by_hop:
        if k in headers:
            del headers[k]

    # accept only supported encodings
    if 'Accept-Encoding' in headers:
        ae = headers['Accept-Encoding']
        filtered_encodings = [x for x in re.split(r',\s*', ae) if x in ('identity', 'gzip', 'x-gzip', 'deflate')]
        headers['Accept-Encoding'] = ', '.join(filtered_encodings)

    del headers['x-account-id']
    for k, v in config['upstreamHeaders'].items():
        headers[k] = v

    return headers


def make_request(url, method, headers={}, data=None, requests=None):
    try:
        # LOG.debug("Sending %s %s with headers: %s and data %s", method, url, headers, data)
        return requests.request(method, url, params=request.args, stream=True, headers=headers, allow_redirects=False,
                                data=data)
    except Exception as e:
        print(e)


@app.route('/proxy/<path:p>', methods=['GET', 'POST'])
def proxy_handler(p):
    account = request.headers['x-account-id']  # TODO: If the header is missing
    account = account.encode('utf-8')  # hack
    for k, v in config['costs'].items():
        print(f"{p}.startswith({k})")
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
                    return serve_proxied(p)
            break
    return "Path not found."


if __name__ == '__main__':
    app.run(debug=True)