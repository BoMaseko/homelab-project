# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements (we'll create it) and script
COPY requirements.txt .
COPY strava-request.py .
COPY strava_tokens.json .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Prometheus metrics port
EXPOSE 9400

# Run the script
CMD ["python3", "strava-request.py"]

