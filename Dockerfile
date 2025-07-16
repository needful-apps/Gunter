FROM python:3.13-slim

ARG CACHEBUST=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 6600

COPY app.py .

CMD ["python", "app.py"]
