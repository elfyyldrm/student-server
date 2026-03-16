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
    with open("submissions.txt", "a") as f:
        f.write(f"{data.student_id} {data.answer}\n")

    return {"status": "received"}
