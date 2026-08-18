FROM python:latest
WORKDIR /api
RUN curl -sSL https://install.python-poetry.org | python3 -
COPY . .
# TODO: maybe add to .bashrc
RUN ~/.local/share/pypoetry/venv/bin/poetry install
EXPOSE 8080
CMD ["poetry", "run", "python", "main.py"]
