"""One-time setup: link your Fidelity account via Plaid Link and print the
resulting access token.

Run this locally (`python scripts/plaid_link.py`), then open
http://localhost:5000 in your browser. You will log in to Fidelity inside
Plaid's own secure widget -- this script and this app never see your
Fidelity username or password, only the access token Plaid issues afterward.

Copy the printed access token into PLAID_ACCESS_TOKEN in your .env file.
"""

import os
import sys

from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from plaid import Configuration, ApiClient, Environment
from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

load_dotenv()

PLAID_CLIENT_ID = os.environ["PLAID_CLIENT_ID"]
PLAID_SECRET = os.environ["PLAID_SECRET"]
PLAID_ENV = os.environ.get("PLAID_ENV", "sandbox")

_ENV_MAP = {
    "sandbox": Environment.Sandbox,
    "development": Environment.Development,
    "production": Environment.Production,
}

configuration = Configuration(
    host=_ENV_MAP[PLAID_ENV],
    api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET},
)
client = plaid_api.PlaidApi(ApiClient(configuration))

app = Flask(__name__)

PAGE = """
<!DOCTYPE html>
<html>
<head><title>Link your Fidelity account</title></head>
<body>
  <button id="link-btn">Link Fidelity account</button>
  <pre id="output"></pre>
  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
  <script>
    fetch('/link_token').then(r => r.json()).then(data => {
      const handler = Plaid.create({
        token: data.link_token,
        onSuccess: (public_token) => {
          fetch('/exchange', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({public_token})
          }).then(r => r.json()).then(resp => {
            document.getElementById('output').textContent =
              'Access token (copy into .env as PLAID_ACCESS_TOKEN):\\n' + resp.access_token;
          });
        },
      });
      document.getElementById('link-btn').onclick = () => handler.open();
    });
  </script>
</body>
</html>
"""


@app.get("/")
def index() -> Response:
    return Response(PAGE, mimetype="text/html")


@app.get("/link_token")
def link_token():
    req = LinkTokenCreateRequest(
        client_name="Fidelity Signal Bot",
        language="en",
        country_codes=[CountryCode("US")],
        user=LinkTokenCreateRequestUser(client_user_id="local-user"),
        products=[Products("investments")],
    )
    resp = client.link_token_create(req)
    return jsonify({"link_token": resp.link_token})


@app.post("/exchange")
def exchange():
    public_token = request.get_json()["public_token"]
    resp = client.item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )
    print("\nACCESS TOKEN (save this to .env as PLAID_ACCESS_TOKEN):")
    print(resp.access_token)
    print()
    return jsonify({"access_token": resp.access_token})


if __name__ == "__main__":
    if PLAID_ENV == "production":
        print("WARNING: PLAID_ENV=production -- this will link your REAL Fidelity account.")
    app.run(port=5000)
