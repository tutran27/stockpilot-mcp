FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip 
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.chat_host.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
