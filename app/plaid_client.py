from plaid import Configuration, ApiClient, Environment
from plaid.api import plaid_api
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest

_ENV_MAP = {
    "sandbox": Environment.Sandbox,
    "development": Environment.Development,
    "production": Environment.Production,
}


def _client(cfg) -> plaid_api.PlaidApi:
    configuration = Configuration(
        host=_ENV_MAP[cfg.PLAID_ENV],
        api_key={"clientId": cfg.PLAID_CLIENT_ID, "secret": cfg.PLAID_SECRET},
    )
    return plaid_api.PlaidApi(ApiClient(configuration))


def get_held_tickers(cfg) -> list[str]:
    """Returns the distinct equity/ETF ticker symbols currently held in the
    linked Fidelity account(s). Cash, bonds, and anything without a resolvable
    ticker symbol are skipped.
    """
    client = _client(cfg)
    request = InvestmentsHoldingsGetRequest(access_token=cfg.PLAID_ACCESS_TOKEN)
    response = client.investments_holdings_get(request)

    securities_by_id = {s.security_id: s for s in response.securities}

    tickers: set[str] = set()
    for holding in response.holdings:
        security = securities_by_id.get(holding.security_id)
        if security and security.ticker_symbol:
            tickers.add(security.ticker_symbol)

    return sorted(tickers)
