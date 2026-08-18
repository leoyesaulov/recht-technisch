FROM python:latest
WORKDIR /api
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${HOME}/.local/bin:${PATH}"

COPY . .
RUN poetry install
EXPOSE 8080
CMD ["poetry", "run", "python", "main.py"]
