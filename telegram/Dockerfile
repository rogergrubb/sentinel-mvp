FROM python:3.11-slim
WORKDIR /app
COPY bridge.py /app/
RUN pip install flask requests
CMD ["python","bridge.py"]
