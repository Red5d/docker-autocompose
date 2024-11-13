FROM python:3.12-alpine
LABEL org.opencontainers.image.source=https://github.com/Red5d/docker-autocompose
WORKDIR /usr/src/app
ENTRYPOINT [ "poetry", "run", "autocompose" ]

RUN apk add --no-cache poetry

COPY poetry.lock pyproject.toml README.md ./
COPY src ./src

RUN poetry install
