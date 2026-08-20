FROM python:3.14.1-slim

WORKDIR /api

ENV POETRY_HOME="/opt/poetry"
ENV PATH="${POETRY_HOME}/bin:${PATH}"

RUN python3 -c "import urllib.request; exec(urllib.request.urlopen('https://install.python-poetry.org').read())"

COPY . .
RUN poetry install

EXPOSE 8080

CMD ["poetry", "run", "python", "api.py"]
