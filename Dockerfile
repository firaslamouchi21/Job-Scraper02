FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
RUN chmod +x /app/start_combined.sh
EXPOSE 8000 8501
CMD ["/app/start_combined.sh"]
