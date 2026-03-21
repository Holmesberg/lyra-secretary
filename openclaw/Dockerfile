FROM python:3.11-slim

WORKDIR /app

# Simple openclaw base environment setup
RUN pip install --no-cache-dir openclaw redis python-telegram-bot httpx

COPY . .

CMD ["python", "-m", "openclaw.cli", "run", "--config", "config/agent.yml"]
