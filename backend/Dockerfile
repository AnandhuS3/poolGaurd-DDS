FROM python:3.11-slim

WORKDIR /app

# System libs: libgl1 is needed by the full opencv-python wheel that ultralytics
# pulls in as a transitive dependency. We install it here so the initial pip
# install succeeds, then we swap to the headless wheel right after.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ultralytics depends on opencv-python (full build with GUI/GL deps).
# Force-swap it for the headless variant so libGL.so.1 is never required
# at import time — without breaking any of ultralytics's other dependencies.
RUN pip install --no-cache-dir --force-reinstall --no-deps \
    opencv-python-headless==4.9.0.80

# Copy application code.
COPY . .

# PORT is injected by Railway at runtime; railway.toml startCommand uses $PORT.
EXPOSE 8000
