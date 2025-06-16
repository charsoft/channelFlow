# 1. Use an official Python runtime as a parent image
# We use -slim-bookworm as it's a small, stable Debian-based image
FROM python:3.11-slim-bookworm

# 2. Set environment variables
# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Ensures Python output is sent straight to the terminal without buffering
ENV PYTHONUNBUFFERED 1

# 3. Install dependencies
# -y flag automatically answers yes to prompts
# --no-install-recommends avoids installing unnecessary packages
# We clean up the apt-get cache to keep the final image small
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# 4. Set the working directory in the container
WORKDIR /app

# 5. Copy and install Python dependencies
# Copying requirements first leverages Docker layer caching
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# 6. Copy the application source code into the container
COPY ./src /app/src

# 7. Command to run the application
# Use 0.0.0.0 to make the app accessible from outside the container
# Cloud Run automatically provides the PORT environment variable, defaulting to 8080
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"] 