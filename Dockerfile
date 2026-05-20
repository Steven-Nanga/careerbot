FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/deploy/docker/run-hourly.sh \
    && mkdir -p /data \
    && useradd --system --create-home --shell /usr/sbin/nologin careerbot \
    && chown -R careerbot:careerbot /app /data

USER careerbot

ENV JOB_SCRAPER_DB=/data/jobs.db
ENV RESUME_DIR=/data/Resumes
ENV SSL_VERIFY=true

CMD ["/app/deploy/docker/run-hourly.sh"]
