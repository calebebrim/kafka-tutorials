FROM python:3.12-alpine

COPY requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /app

COPY src /app


EXPOSE 8080
WORKDIR /app
 
CMD ["python", "main.py"]
