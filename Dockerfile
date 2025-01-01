# Start from an official Python runtime
FROM python:3.10-slim

# Create a working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt /app/

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . /app

# Expose the port that Flask listens on (default 5000)
EXPOSE 5000

# Run the Flask app (app.py must be in /app)
CMD ["python", "app.py"]
