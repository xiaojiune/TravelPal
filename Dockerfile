FROM ubuntu:latest
LABEL authors="changzi"

ENTRYPOINT ["top", "-b"]