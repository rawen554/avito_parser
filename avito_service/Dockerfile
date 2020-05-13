FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN apt-get update && apt-get install -y python3-dev

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get install -y locales
RUN cat /etc/locale.gen | grep ru_RU.UTF-8 | cut -c 3- >> /etc/locale.gen && locale-gen
RUN export LANG=ru_RU.UTF-8

COPY . .

CMD [ "python", "-u", "./main.py" ]