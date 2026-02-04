FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any are needed (e.g., for some langchain integrations)
RUN apt-get update && apt-get install -y --no-install-recommends 
    build-essential 
    && rm -rf /var/lib/apt/lists/*

# Copy the project files
COPY pyproject.toml .
COPY src/ ./src/
COPY start.sh .
# Copy messages.txt if it exists, or it will be created with defaults in api.py
COPY messages.txt* ./

# Install the package and its dependencies
RUN pip install --no-cache-dir .

# Make start script executable
RUN chmod +x start.sh

# Expose the API port
EXPOSE 8000

# Run the start script
CMD ["./start.sh"]
