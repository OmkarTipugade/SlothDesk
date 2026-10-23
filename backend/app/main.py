from fastapi import FastAPI

app = FastAPI(title="SlothDesk API")


@app.get("/")
def root():
    return {"message": "Welcome to SlothDesk!"}


@app.get("/health")
def health():
    return {"status": "ok"}