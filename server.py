from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
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
    ad: str
    soyad: str
    yas: int
    ilgi_alanlari: list[str]


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
                    ad TEXT,
                    soyad TEXT,
                    yas INTEGER,
                    ilgi_alanlari JSONB,
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
    server_note = "JSON verisi alındı ve işlendi."
    status = "processed"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO submissions
                (type, ad, soyad, yas, ilgi_alanlari, original_filename, content_json, server_note, processed_at, status)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s, %s)
                RETURNING id
            """, (
                "json",
                data.ad,
                data.soyad,
                data.yas,
                json.dumps(data.ilgi_alanlari, ensure_ascii=False),
                None,
                json.dumps(data.model_dump(), ensure_ascii=False),
                server_note,
                processed_at,
                status
            ))
            submission_id = cur.fetchone()[0]
        conn.commit()

    return {
        "id": submission_id,
        "type": "json",
        "ad": data.ad,
        "soyad": data.soyad,
        "yas": data.yas,
        "ilgi_alanlari": data.ilgi_alanlari,
        "server_note": server_note,
        "processed_at": processed_at.isoformat(),
        "status": status
    }


@app.post("/submit-file")
async def submit_file(file: UploadFile = File(...)):
    if not server_open_now():
        raise HTTPException(
            status_code=403,
            detail="Server is closed right now. Try again during open hours."
        )

    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Please upload a .json file")

    content = await file.read()

    try:
        data = json.loads(content.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    processed_at = datetime.now(TIMEZONE)
    server_note = "Dosya server tarafından işlendi."
    status = "processed"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO submissions
                (type, ad, soyad, yas, ilgi_alanlari, original_filename, content_json, server_note, processed_at, status)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s, %s)
                RETURNING id
            """, (
                "file",
                data.get("ad"),
                data.get("soyad"),
                data.get("yas"),
                json.dumps(data.get("ilgi_alanlari", []), ensure_ascii=False),
                file.filename,
                json.dumps(data, ensure_ascii=False),
                server_note,
                processed_at,
                status
            ))
            submission_id = cur.fetchone()[0]
        conn.commit()

    modified_data = dict(data)
    modified_data["id"] = submission_id
    modified_data["server_note"] = server_note
    modified_data["processed_at"] = processed_at.isoformat()
    modified_data["status"] = status

    return JSONResponse(content=modified_data)


@app.get("/submissions")
def get_submissions():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, type, ad, soyad, yas, ilgi_alanlari, original_filename,
                       content_json, server_note, processed_at, status
                FROM submissions
                ORDER BY id DESC
            """)
            rows = cur.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "type": row[1],
            "ad": row[2],
            "soyad": row[3],
            "yas": row[4],
            "ilgi_alanlari": row[5],
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
                SELECT id, type, ad, soyad, yas, ilgi_alanlari, original_filename,
                       content_json, server_note, processed_at, status
                FROM submissions
                ORDER BY id DESC
            """)
            rows = cur.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "type": row[1],
            "ad": row[2],
            "soyad": row[3],
            "yas": row[4],
            "ilgi_alanlari": row[5],
            "original_filename": row[6],
            "content_json": row[7],
            "server_note": row[8],
            "processed_at": row[9].isoformat() if row[9] else None,
            "status": row[10]
        })

    return JSONResponse(content=result)
