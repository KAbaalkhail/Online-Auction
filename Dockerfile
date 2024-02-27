# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the timezone environment variable
ENV TZ=Asia/Riyadh

# Install tzdata package
RUN apt-get update && apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && dpkg-reconfigure -f noninteractive tzdata

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app code into the container at /app
COPY src/flask-website/ .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable for the Flask application
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run the Flask app
CMD ["flask", "run"]
