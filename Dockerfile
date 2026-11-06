FROM python:3.11-slim

# Prevent Python from writing bytecode and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime system packages: FFmpeg with libass, fontconfig, DejaVu fonts, curl, git
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass9 \
    libass-dev \
    fonts-freefont-ttf \
    fonts-dejavu-core \
    fontconfig \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Inter & custom fonts in /usr/share/fonts/truetype/custom/
RUN mkdir -p /usr/share/fonts/truetype/custom
COPY assets/fonts/* /usr/share/fonts/truetype/custom/
RUN fc-cache -f -v

WORKDIR /app

# Install Python dependencies first for caching layers
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary application and staging directories
RUN mkdir -p /app/data \
             /app/output/youtube \
             /app/output/tiktok \
             /app/temp \
             /app/logs \
             /tmp/yt_automation

# Run as an unprivileged user (bind-mounted dirs must be writable by UID 1000)
RUN useradd --create-home --uid 1000 svuser && chown -R svuser:svuser /app /tmp/yt_automation

# Copy application source code
COPY config/ ./config/
COPY core/ ./core/
COPY services/ ./services/
COPY engine/ ./engine/
COPY scripts/ ./scripts/
COPY assets/ ./assets/
COPY main.py .
USER svuser

# Default command: continuous weekly rotation scheduler daemon
CMD ["python", "scripts/scheduler.py"]
