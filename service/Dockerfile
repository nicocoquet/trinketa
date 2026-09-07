FROM python:3.12-slim

WORKDIR /app
COPY service/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY service ./service

USER 65534
EXPOSE 8000
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
