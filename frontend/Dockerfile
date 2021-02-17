FROM python:3

WORKDIR /usr/src/app

COPY ./frontend .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "__main__.py"]

EXPOSE 2222/tcp
