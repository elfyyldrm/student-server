from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from datetime import datetime
from zoneinfo import ZoneInfo
import json

app = FastAPI()

TIMEZONE = ZoneInfo("Europe/Istanbul")
OPEN_HOUR = 9
CLOSE_HOUR = 17

def server_open_now() -> bool:
    now = datetime.now(TIMEZONE)
    return OPEN_HOUR <= now.hour < CLOSE_HOUR

@app.get("/")
def home():
    now = datetime.now(TIMEZONE)
    return {
        "message": "Server is running",
        "current_time": now.isoformat(),
        "server_accepting_requests": server_open_now()
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

    data["server_note"] = "Dosya server tarafından işlendi."
    data["processed_at"] = datetime.now(TIMEZONE).isoformat()
    data["status"] = "processed"

    return JSONResponse(content=data)
