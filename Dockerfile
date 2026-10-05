FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app

COPY requirements-render.txt ./
RUN pip install --no-cache-dir -r requirements-render.txt

COPY . ./

EXPOSE 10000

CMD ["sh", "-c", "chainlit run backend_server.py --host 0.0.0.0 --port ${PORT}"]
