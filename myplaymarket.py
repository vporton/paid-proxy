import base64

import requests
from flask import request, jsonify

from common import app, config, OurDB, fund_account


class PurchaseTokensDB:
    def __enter__(self):
        self.tokens_db = self.env.open_db(b'android.purchase_tokens', create=True)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.env.close()


@app.route('/playmarket_rtdn', methods=['POST'])
def playmarket_notification():
    data = request.json()['message']['data']
    j2 = base64.b64decode(data)
    package_name = j2['packageName']
    sku = j2['sku']
    if package_name != config['android']['packageName']:
        raise Exception("Wrong package name")
    notification = j2['oneTimeProductNotification']
    if notification != 1:  # ONE_TIME_PRODUCT_PURCHASED
        raise Exception("Product not purchased")
    if sku != config['android']['sku']:
        raise Exception("Wrong product SKU")
    purchase_token = j2['purchaseToken']  # globally unique
    with OurDB() as our_db:
        with PurchaseTokensDB() as pt_db:
            with our_db.env.begin(pt_db.tokens_db, write=True) as txn:  # TODO: buffers=True allowed?
                dummy = txn.get(purchase_token)
                if dummy is not None:
                    raise Exception("Purchase token is already used")
                txn.put(purchase_token, b'')

        # We check that the RTDN is not from a hacker:
        response = requests.get(f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{package_name}/purchases/products/{sku}/tokens/{purchase_token}")
        if not response.ok():
            raise Exception("Can't contact Google")
        product_purchase = response.json()['resource']  # ProductPurchase, see https://developers.google.com/android-publisher/api-ref/rest/v3/purchases.products
        if product_purchase['purchaseState'] != 0:  # purchased
            raise Exception("Not purchased")

        amount = product_purchase['quantity'] * config['android']['unitPrice']
        account = product_purchase['developerPayload']
        fund_account(our_db, account, amount)
        return jsonify(success=True)
