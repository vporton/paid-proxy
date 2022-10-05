from flask import request, jsonify
import stripe

from common import fund_account, OurDB


@app.route('/stripe_webhooks', methods=['POST'])
def stripe_webhook():
    event = None
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config['stripe']['secret']
        )
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e

    # Handle the event
    if event.type == 'payment_intent.succeeded':
        amount = event['data']['object']['amount'] / 100
        account = event['data']['metadata']['account']
        with OurDB() as our_db:
            fund_account(our_db, account, amount)

    return jsonify(success=True)


