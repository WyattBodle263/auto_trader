FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY main.py auto_trade.py ./

# Override with `CMD ["python", "main.py"]` (or set Railway's start command)
# to run the advisory-only/Fidelity script instead.
CMD ["python", "auto_trade.py"]
