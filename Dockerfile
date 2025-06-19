# Stage 1: Build the Svelte frontend
FROM node:18-slim AS builder

# Set the working directory for the frontend
WORKDIR /app/frontend

# Copy package.json and package-lock.json first to leverage Docker caching
COPY frontend/package*.json ./
RUN npm ci

# Copy the rest of the frontend source code
COPY frontend/ ./

# Build the frontend application
RUN npm run build


# Stage 2: Build the Python backend
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies (e.g., ffmpeg, git)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory for the application
WORKDIR /app

# Copy Python dependencies and install them
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the Python source code
COPY src/ ./src/

# Copy the built frontend from the builder stage
COPY --from=builder /app/frontend/dist ./frontend/dist

# Expose the port the app will run on
EXPOSE 8080

# Command to run the application
# Cloud Run automatically provides the PORT environment variable
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"] 