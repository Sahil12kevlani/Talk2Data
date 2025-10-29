from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Talk2Data API setup successful!"}
