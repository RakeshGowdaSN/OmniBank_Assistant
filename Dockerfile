# Dockerfile
# Build context is assumed to be this 'app/' directory.

# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set a general working directory.
#    This directory will be the parent of your 'app' package inside the container.
# WORKDIR /service_root

# 4. Copy requirements.txt from the build context (app/) into WORKDIR (/service_root)
#    and install dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the .env file into the app directory within the container
# COPY .env ./app/.env  # <--- ADD THIS LINE

# 5. Copy all content from the current build context (which is the host's 'app/' directory)
#    into a subdirectory named 'app' within the WORKDIR.
#    So, files like server.py (from host: app/server.py) will go to container: /service_root/app/server.py
#    And agent.py (from host: app/agent.py) will go to container: /service_root/app/agent.py
# COPY . ./app/
COPY . .

# 6. Expose the port the app runs on
EXPOSE 8002

# 7. Define the command to run your application.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
