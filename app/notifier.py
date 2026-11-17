from twilio.rest import Client

from .strategy import Signal


def send_signal(signal: Signal, cfg) -> None:
    client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
    body = f"[{signal.symbol}] {signal.action}: {signal.reason}"
    client.messages.create(
        body=body,
        from_=cfg.TWILIO_FROM_NUMBER,
        to=cfg.TWILIO_TO_NUMBER,
    )
