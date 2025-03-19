FROM python:3.13-alpine3.21
WORKDIR /trader_app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
ENTRYPOINT ["python", "main.py"]