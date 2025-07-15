FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Expose the port the app runs on
EXPOSE 6600

# Command to run the application
CMD ["python", "app.py"]
