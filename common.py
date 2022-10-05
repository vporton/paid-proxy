import json
import struct

import lmdb

with open("config.json") as config_file:
    config = json.load(config_file)


class OurDB:
    def __enter__(self):
        # NFS filesystem safe lock
        self.lock = Lock(f"{config['statePath']}/mylock")
        self.lock.lock(timeout=4)  # FIXME: Ensure, it is not unlocked in the middle.

        self.env = lmdb.open(config['statePath'], max_dbs=10, map_size=200*1024*1024*1024)
        self.accounts_db = self.env.open_db(b'accounts', create=True)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.env.close()
        self.lock.unlock()


def fund_account(our_db, account, amount):
    with our_db.env.begin(our_db.accounts_db, write=True) as txn:  # TODO: buffers=True allowed?
        remainder = txn.get(account)
        if remainder is None:
            remainder = 0.0
        else:
            remainder = struct.unpack('f', remainder)[0]  # float
        txn.put(account, struct.pack('f', remainder + amount))
