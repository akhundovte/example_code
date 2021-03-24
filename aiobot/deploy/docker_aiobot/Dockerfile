FROM python:3.7

RUN pip install --upgrade pip
ADD requirements.txt /sandbox/requirements.txt
RUN pip install -r /sandbox/requirements.txt

RUN apt-get update && apt-get install -y mc

RUN groupadd -g 1003 manager
RUN useradd -l -u 1002 -g manager manager

RUN usermod -d /home/manager manager
RUN chown -R manager:manager /home/manager
RUN chmod 755 /home/manager

USER manager