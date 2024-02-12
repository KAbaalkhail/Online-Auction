# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# First, copy only the requirements.txt file to the /app directory and install the Python dependencies.
# This allows Docker to cache the installed dependencies as a separate layer, which is more efficient.
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Now, copy the rest of the application into the /app directory
COPY ./src/flask-website /app

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run app.py when the container launches
CMD ["flask", "run"]
