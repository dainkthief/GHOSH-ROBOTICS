# --------------------------
# GHOSH ROBOTICS Dockerfile
# --------------------------
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt || true

# Default command
CMD ["python", "main.py"]
