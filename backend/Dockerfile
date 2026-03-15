FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV and PostgreSQL
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY config/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p assets/weights assets/uploads dlogs

# Copy application files
COPY . .

ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose backend port
EXPOSE 8000

CMD ["python", "main.py"]
