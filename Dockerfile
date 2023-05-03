FROM python:3.10.11-bullseye

WORKDIR /usr/local/src/chatbot

COPY . .

RUN pip install -r requirements.txt

CMD ["python","main.py","-d"]