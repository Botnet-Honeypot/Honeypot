FROM docker

WORKDIR /usr/src/backend

RUN apk add python3 py3-pip

COPY . .

RUN pip install -r requirements.txt

CMD ["python3", "-m", "backend"]