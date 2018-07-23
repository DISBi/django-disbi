FROM python:3.6-stretch


RUN python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    rm -r /root/.cache && \
    pip install -e git+https://github.com/disbi/django-disbi.git#egg=django-disbi

RUN apt-get update \ 
    && apt-get install -y postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
ADD ./requirements.txt /app/requirements.txt
WORKDIR /app/
RUN pip install -r requirements.txt

WORKDIR /
ADD ./ /app/
WORKDIR /app/



RUN ["chmod", "+x", "./entry.sh"]

ENTRYPOINT [ "./entry.sh" ]
