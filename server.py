from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json
import psycopg

app = FastAPI()

TIMEZONE = ZoneInfo("Europe/Istanbul")
OPEN_HOUR = 9
CLOSE_HOUR = 17
DATABASE_URL = os.getenv("DATABASE_URL")


class StudentInfo(BaseModel):
    first_name: str
    last_name: str
    age: int
    interests: list[str]

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v):
        if not v or not v.strip():
            raise ValueError("This field cannot be empty.")
        return v.strip()

    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if not isinstance(v, int) or v <= 0:
            raise ValueError("Age must be a positive integer.")
        return v

    @field_validator("interests")
    @classmethod
    def validate_interests(cls, v):
        if not isinstance(v, list) or len(v) < 3:
            raise ValueError("Interests must be a list with at least 3 items.")
        return v


def server_open_now() -> bool:
    now = datetime.now(TIMEZONE)
    return OPEN_HOUR <= now.hour < CLOSE_HOUR


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(DATABASE_URL)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id SERIAL PRIMARY KEY,
                    type TEXT NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    age INTEGER,
                    interests JSONB,
                    original_filename TEXT,
                    content_json JSONB,
                    server_note TEXT,
                    processed_at TIMESTAMPTZ,
                    status TEXT
                )
            """)
        conn.commit()


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def home():
    now = datetime.now(TIMEZONE)
    return {
        "message": "Server is running",
        "current_time": now.isoformat(),
        "server_accepting_requests": server_open_now()
    }


@app.post("/submit")
def submit_json(data: StudentInfo):
    if not server_open_now():
        raise HTTPException(
            status_code=403,
            detail="Server is closed right now. Try again during open hours."
        )

    processed_at = datetime.now(TIMEZONE)
    server_note = "Your JSON data was received and processed by the server."
    status = "processed"

    response_payload = {
        "first_name": data.first_name,
        "last_name": data.last_name,
        "age": data.age,
        "interests": data.interests,
        "submission_type": "json",
        "server_note": server_note,
        "processed_at": processed_at.isoformat(),
        "status": status
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO submissions
                (type, first_name, last_name, age, interests, original_filename, content_json, server_note, processed_at, status)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s, %s)
                RETURNING id
            """, (
                "json",
                data.first_name,
                data.last_name,
                data.age,
                json.dumps(data.interests, ensure_ascii=False),
                None,
                json.dumps(response_payload, ensure_ascii=False),
                server_note,
                processed_at,
                status
            ))
            submission_id = cur.fetchone()[0]
        conn.commit()

    response_payload["id"] = submission_id
    return response_payload


@app.post("/submit-file")
async def submit_file(file: UploadFile = File(...)):
    if not server_open_now():
        raise HTTPException(
            status_code=403,
            detail="Server is closed right now. Try again during open hours."
        )

    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Please upload a .json file.")

    content = await file.read()

    try:
        raw_data = json.loads(content.decode("utf-8"))
        data = StudentInfo(**raw_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON content: {str(e)}")

    processed_at = datetime.now(TIMEZONE)
    server_note = "Your file was received and processed by the server."
    status = "processed"

    modified_data = {
        "first_name": data.first_name,
        "last_name": data.last_name,
        "age": data.age,
        "interests": data.interests,
        "submission_type": "file",
        "original_filename": file.filename,
        "server_note": server_note,
        "processed_at": processed_at.isoformat(),
        "status": status
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO submissions
                (type, first_name, last_name, age, interests, original_filename, content_json, server_note, processed_at, status)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s, %s)
                RETURNING id
            """, (
                "file",
                data.first_name,
                data.last_name,
                data.age,
                json.dumps(data.interests, ensure_ascii=False),
                file.filename,
                json.dumps(modified_data, ensure_ascii=False),
                server_note,
                processed_at,
                status
            ))
            submission_id = cur.fetchone()[0]
        conn.commit()

    modified_data["id"] = submission_id
    return JSONResponse(content=modified_data)


@app.get("/submissions")
def get_submissions():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, type, first_name, last_name, age, interests,
                       original_filename, content_json, server_note, processed_at, status
                FROM submissions
                ORDER BY id DESC
            """)
            rows = cur.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "type": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "age": row[4],
            "interests": row[5],
            "original_filename": row[6],
            "content_json": row[7],
            "server_note": row[8],
            "processed_at": row[9].isoformat() if row[9] else None,
            "status": row[10]
        })

    return result


@app.get("/download-submissions")
def download_submissions():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, type, first_name, last_name, age, interests,
                       original_filename, content_json, server_note, processed_at, status
                FROM submissions
                ORDER BY id DESC
            """)
            rows = cur.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "type": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "age": row[4],
            "interests": row[5],
            "original_filename": row[6],
            "content_json": row[7],
            "server_note": row[8],
            "processed_at": row[9].isoformat() if row[9] else None,
            "status": row[10]
        })

    return JSONResponse(content=result)
