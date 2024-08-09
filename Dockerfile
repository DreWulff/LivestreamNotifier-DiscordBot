# Use the official Node.js image as a base image
FROM python:3-alpine3.20

# Create and change to the app directory
WORKDIR /usr/src/app

# Install dependencies
RUN pip install discord.py
RUN pip install requests
RUN pip install python-dotenv

# Copy the application code
COPY . .

# Setup the database
RUN python database.py

# Command to run the application
CMD ["python", "bot.py"]