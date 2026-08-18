FROM python:latest
WORKDIR /api
COPY . .
RUN curl -sSL https://install.python-poetry.org | python3 - &&\
    export PATH="/root/.local/bin:$PATH" && \
    poetry install
EXPOSE 8080
CMD poetry run python main.py
