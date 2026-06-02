FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir requests
COPY signal_server.py .
EXPOSE 5000 5001
CMD ["python", "-u", "signal_server.py"]
