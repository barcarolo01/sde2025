import os
from flask import Flask, render_template_string, request
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth

BUSINESS_PAYPAL_ID = os.environ.get("BUSINESS_PAYPAL_ID")
BUSINESS_PAYPAL_SECRET = os.environ.get("BUSINESS_PAYPAL_SECRET")

app = Flask(__name__)

# This function fetches a new access token from PayPal sandbox using the credentials of the seller account
def get_access_token():
    TOKEN_URL = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    auth = HTTPBasicAuth(BUSINESS_PAYPAL_ID, BUSINESS_PAYPAL_SECRET)
    token_data = {"grant_type": "client_credentials"}
    token_res = requests.post(TOKEN_URL, data=token_data, auth=auth)
    return token_res.json()["access_token"]

# Homepage route
@app.route("/")
def homepage():
    return "PAYPAL PAYMENT SERVICE RUNNING"

# Order confirmation router
@app.route("/confirm_order")
def confirm_order():
    order_id = request.args.get("token")
    if not order_id:
        return "Missing order token", 400

    html_content = f"""
    <h1>Confirm Your Payment</h1>
    <p>Order ID: {order_id}</p>
    <form action="/success" method="get">
        <input type="hidden" name="token" value="{order_id}">
        <button type="submit">PAY</button>
    </form>
    <form action="/cancel" method="post">
        <input type="hidden" name="token" value="{order_id}">
        <button type="submit">CANCEL</button>
    </form>
    """
    return render_template_string(html_content)


@app.route("/success")
def payment_success():
    order_id = request.args.get("token")
    if not order_id:
        return "Missing order token", 400

    access_token = get_access_token()

    CAPTURE_URL = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    capture_res = requests.post(CAPTURE_URL, headers=headers)
    capture_data = capture_res.json()

    status = capture_data["status"]
    customer_name = capture_data["payer"]["name"]["given_name"] + " " + capture_data["payer"]["name"]["surname"]
    price_paid = capture_data["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]
    datetime_paid = capture_data["purchase_units"][0]["payments"]["captures"][0]["create_time"]

    if status.upper() == "COMPLETED":
        returned_msg = f"""
        <h1>Payment Successfully Completed</h1>
        <p>Status: {status}</p>
        <p>Customer: {customer_name}</p>
        <p>Amount: {price_paid} €</p>
        <p>Datetime: {datetime_paid}</p>
        <p>You can now return to Telegram to get your QR code!</p>\
        """
    else:
        returned_msg = "<h1>Payment Refused</h1><p>Please try later.</p>"

    # TODO: Insert payment details into your database here

    return render_template_string(returned_msg)

@app.route("/cancel", methods=["GET", "POST"])
def cancel():
    return 'Payment canceled!'

@app.route("/webhook/paypal", methods=["POST"])
def paypal_webhook():
    event = request.json  # PayPal sends JSON
    event_type = event.get("event_type")
    print("RECEIVED SOMETHING FROM PAYPAL WEBHOOK: ", event_type)
    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        capture = event["resource"]
        payer_name = capture["payer"]["name"]["given_name"] + " " + capture["payer"]["name"]["surname"]
        amount = capture["amount"]["value"]
        currency = capture["amount"]["currency_code"]
        datetime_paid = capture["create_time"]
        print(f"[!] Payment received: {payer_name}, {amount} {currency}, at {datetime_paid}")
        # Insert into your DB here

    return "", 200  # Must return 200 to acknowledge PayPal

if __name__ == '__main__':
    load_dotenv()  # Loads variables from .env into environment
    app.run(host='0.0.0.0', port=6000, debug=True)