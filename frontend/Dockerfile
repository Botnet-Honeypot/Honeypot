FROM python:3

WORKDIR /usr/src/frontend

RUN apt-get update && apt-get install -y python3-pip

COPY . .

RUN ./genkeys

RUN pip3 install -r requirements.txt

CMD ["python3", "-m", "frontend"]