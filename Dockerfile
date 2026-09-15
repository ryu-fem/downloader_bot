# Base image with Python
FROM python:3.12-slim

# ffmpeg is required by yt-dlp for merging video+audio and mp3 conversion
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# BOT_TOKEN is provided as an environment variable in Railway's dashboard,
# not baked into the image.
CMD ["python", "bot.py"]
