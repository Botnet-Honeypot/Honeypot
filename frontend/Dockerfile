FROM python:3

WORKDIR /usr/src/frontend

COPY . .

RUN ./genkeys

RUN apt-get update && apt-get install -y python3-pip

RUN pip3 install -r requirements.txt

CMD ["python3", "-m", "frontend"]