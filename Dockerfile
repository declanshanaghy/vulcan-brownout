FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    aiohttp==3.9.1 \
    aiohttp-cors==0.7.0 \
    websockets==12.0 \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    python-dotenv==1.0.0 \
    flake8==6.1.0 \
    mypy==1.7.1

# Copy source code
COPY development/src /app/development/src
COPY quality/scripts /app/quality/scripts

# Set Python path
ENV PYTHONPATH=/app

CMD ["pytest"]
