FROM debian:buster

#RUN apt-get update && apt-get install --yes python3 && apt-get clean

RUN apt-get update
RUN apt-get install --yes curl
RUN apt-get install --yes python3 python3-nbformat python3-nbconvert python3-ipykernel
RUN apt-get install --yes python3-requests python3-xmltodict python3-yaml
RUN apt-get install --yes jupyter-core jupyter-nbconvert

# kpt requires git
RUN apt-get install --yes git vim

ADD jupyter /jupyter
ADD lib/ /lib
ADD ssh/ /root/.ssh

ADD run.py /run.py

ENTRYPOINT [ "/run.py" ]


