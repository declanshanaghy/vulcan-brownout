FROM python:3.11-slim

WORKDIR /mock_ha

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .
COPY fixtures.py .

# Health check
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('localhost', 8123), timeout=2)" || exit 1

# Run mock server
EXPOSE 8123
CMD ["python", "server.py"]
