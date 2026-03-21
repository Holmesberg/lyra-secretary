from fastapi import FastAPI
from app.api.v1.router import api_router

app = FastAPI(
    title="Lyra Secretary API",
    version="1.1",
    description="Adaptive scheduler and personal cognitive operating system"
)

app.include_router(api_router, prefix="/v1")

@app.get("/")
def root():
    return {"message": "Lyra Secretary API is running"}
