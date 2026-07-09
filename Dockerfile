FROM ubuntu:24.04

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        ffmpeg \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y python3-pip


WORKDIR /app

COPY requirements.txt .

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN python3 -m pip install --no-cache-dir -U pip setuptools wheel \
 && python3 -m pip install --no-cache-dir -r requirements.txt \
 && rm -f requirements.txt


COPY ./bot ./

CMD ["python", "bot.py"]