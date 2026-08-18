from fastapi import FastAPI
import uvicorn
app = FastAPI()

@app.get("/")
def main():
    return {"name": "Legal Loves Tech 2026", "message": "Hello World!"}

uvicorn.run(app, host="0.0.0.0", port=8080)
