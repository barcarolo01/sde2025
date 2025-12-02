import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

def test_paypal():
    # Redirect URLs (InstaTunnel)
    RETURN_URL = "https://barcarolograziadei-payment.instatunnel.my/confirm_order"
    CANCEL_URL = "https://barcarolograziadei-payment.instatunnel.my/cancel"

    # PayPal API URLs
    TOKEN_URL = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    ORDER_URL = "https://api-m.sandbox.paypal.com/v2/checkout/orders"

    # Loads variables from .env file (ID and SECRET of the seller paypal sandbox account)
    load_dotenv()  
    BUSINESS_PAYPAL_ID = os.environ.get("BUSINESS_PAYPAL_ID")
    BUSINESS_PAYPAL_SECRET = os.environ.get("BUSINESS_PAYPAL_SECRET")    

    # Generate access token
    auth = HTTPBasicAuth(BUSINESS_PAYPAL_ID, BUSINESS_PAYPAL_SECRET)
    token_data = {"grant_type": "client_credentials"}
    token_res = requests.post(TOKEN_URL, data=token_data, auth=auth)
    access_token = token_res.json()["access_token"]

    # Create the order
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # Content and price of the order (Maybe to be stored in an external json file?)
    order_payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "description": "Lezione singola",   # Description of the product
                "amount": {
                    "currency_code": "EUR",
                    "value": "50.00"    # Price (EURO)
                }
            }
        ],
        "application_context": {
            "return_url": RETURN_URL,   # URL to redirect the buyer after approval
            "cancel_url": CANCEL_URL # URL to redirect the buyer after cancellation
        }
    }

    order_res = requests.post(ORDER_URL, json=order_payload, headers=headers)
    order = order_res.json()

    # Extract the redirect link from the json response
    approve_link = next(link["href"] for link in order["links"] if link["rel"] == "approve")
    return approve_link