FROM python:latest
WORKDIR /api
RUN curl -sSL https://install.python-poetry.org | python3 -
EXPOSE 8080
COPY . .
# TODO: maybe add to .bashrc
RUN ~/.local/share/pypoetry/venv/bin/poetry install
CMD ["poetry", "run", "python", "main.py"]
