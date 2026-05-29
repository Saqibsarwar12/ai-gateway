FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_cache_dir=1

# Install deps with explicit pip3
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ ./app/
COPY start.sh .

RUN chmod +x start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
