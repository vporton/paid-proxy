# Paid Proxy

Proxy intended for Google Maps that limit the quantity of requests
accordingly the sum paid by the user through Stripe.

**Warning:** the support for in-app purchases is not yet debugged,
because Google is slow to answer bug reports and support requests.

This app can be run on a server or (presumably less expensively) as
an AWS lambda with DB stored in an EFS.

## Demo session

```
$ curl http://127.0.0.1:5000/balance/xxx ;echo
0.0
$ curl -H "X-Account-Id: xxx" 'http://127.0.0.1:5000/proxy/xxx/maps/api/place/nearbysearch/json?location=-33.8670,151.1957&radius=500' ;echo
Payment required
$ curl -d '' -H 'X-Admin-Secret: boi4gohth*ie?t<ah5johhu3eis1Co1m' http://127.0.0.1:5000/imitated-purchase/xxx/7.0
{
  "success": true
}
$ curl http://127.0.0.1:5000/balance/xxx ;echo
7.0
$ curl -H "X-Account-Id: xxx" 'http://127.0.0.1:5000/proxy/xxx/maps/api/place/nearbysearch/json?location=-33.8670,151.1957&radius=500'
{
   ...
   "status" : "OK"
}
$ curl http://127.0.0.1:5000/balance/xxx ;echo
6.8639984130859375
```
