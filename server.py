from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

submissions = []

class Submission(BaseModel):
    student_id: str
    answer: str

@app.get("/")
def home():
    return {"message": "Server is running"}

@app.post("/submit")
def submit(data: Submission):
    submissions.append(data)
    return {"status": "received"}

@app.get("/submissions")
def get_submissions():
    return submissions
