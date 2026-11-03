FROM python:3.11-slim

# Prevent Python from writing bytecode and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime system packages: FFmpeg, TrueType fonts, and utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-freefont-ttf \
    fonts-dejavu-core \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for caching layers
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY config/ ./config/
COPY core/ ./core/
COPY services/ ./services/
COPY engine/ ./engine/
COPY main.py .

# Create tokens directory placeholder & tmp working folder
RUN mkdir -p /app/tokens /tmp/yt_automation

ENTRYPOINT ["python", "main.py"]
