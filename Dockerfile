FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fordlogger/ fordlogger/
COPY sql/ sql/

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python -c "import psycopg2; c=psycopg2.connect(host='db',dbname='fordlogger',user='fordlogger',password='fordlogger'); c.close()" || exit 1

CMD ["python", "-m", "fordlogger"]
