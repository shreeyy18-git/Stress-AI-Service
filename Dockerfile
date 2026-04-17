# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if any are needed
# slim images are bare, but for these libraries we are likely okay
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
# Northflank will override this with the PORT env var, but 8000 is a good default
EXPOSE 8000

# Run the application
# We use 0.0.0.0 to bind to all interfaces in the container
# Use the PORT environment variable if provided by the host
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
