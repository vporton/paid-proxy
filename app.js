'use strict'

const express = require('express');
const fs = require('fs');
//const JSON = require('JSON');
const app = express();

const config = JSON.parse(fs.loadFileSync("config.json"));

let env = new lmdb.Env();
env.open({
    path: "/mnt/persist/db",
    mapSize: 200*1024*1024*1024, // maximum database size
    maxDbs: 10,
});
let dbi = env.openDbi({
    name: "accounts",
    create: true,
});

app.get('/', (req, res) => {
    res.send('This is a proxy server.');
});

function serveProxied(req, res, upstreamPath) {
    for (let h in res.headers??) {
        res.append(TODO, TODO);
    }
}

app.get(/\/proxy\/.*/', (req, res) => {
    const m = /\/proxy\/(.*)/.match(req.url);
    const upstreamPath = m[1];
    let account = req.headers['X-Account-Id'].value;
    if (account === undefined) {
        res.send('Missing account ID.');
        return;
    }
    for (let k of Object.keys(config.costs.keys)) {
        if (upstreamPath.startsWith(k)) {
            let txn = env.beginTxn();
            let remainder = txn.getNumber(dbi, account);
            if (config.costs[k] <= remainder) {
                txn.setNumber(dbi, account, remainder - config.costs[k]);
                serveProxied(req, res, upstreamPath);
            }
            txn.commit();
        }
    }
})

dbi.close()
env.close()

module.exports = app