FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./gateway /app/gateway

ENV PYTHONPATH=/app

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "4000", "--reload"]