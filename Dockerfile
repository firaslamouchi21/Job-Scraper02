FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
EXPOSE 8501
CMD ["python","-m","streamlit","run","app.py","--server.port=8501","--server.address=0.0.0.0"]
