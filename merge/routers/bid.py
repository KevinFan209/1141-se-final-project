from fastapi import APIRouter, UploadFile, File
import uuid, os

router = APIRouter(prefix="/bids")

UPLOAD_DIR = "uploads/proposals"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
def create_bid(project_id: int, price: int, file: UploadFile = File(...)):
    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return {"message": "Bid submitted", "file": filename}
