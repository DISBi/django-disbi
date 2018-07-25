FROM python:3.6-stretch


RUN python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    rm -r /root/.cache
    
RUN apt-get update \ 
    && apt-get install -y postgresql-client \
    && curl -sL https://deb.nodesource.com/setup_10.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g sass

WORKDIR /
ADD ./requirements.txt /django-disbi/requirements.txt
WORKDIR /django-disbi/
RUN pip install -r requirements.txt

WORKDIR /
ADD ./ /django-disbi/
WORKDIR /django-disbi/



RUN ["chmod", "+x", "./entry.sh"]

ENTRYPOINT [ "./entry.sh" ]
