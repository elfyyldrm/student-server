from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Submission(BaseModel):
    student_id: str
    answer: str

@app.get("/")
def home():
    return {"message": "Server is running"}

@app.post("/submit")
def submit(data: Submission):
    print("New submission:", data)
    return {
        "status": "received",
        "student_id": data.student_id
    }
