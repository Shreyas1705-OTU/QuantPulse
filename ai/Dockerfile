FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No default CMD -- this image runs two distinct one-shot jobs
# (explainer.py, daily_summary.py), each its own CronJob with its own
# `command` in k8s/ai/. See explainer-cronjob.yaml / daily-summary-cronjob.yaml.
