from fastapi import FastAPI

app = FastAPI(
    title="Lyra Secretary",
    version="1.1",
    description="Adaptive scheduler and personal cognitive operating system"
)

@app.get("/")
def root():
    return {"message": "Lyra Secretary API is running"}
