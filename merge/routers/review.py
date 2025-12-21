from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Review

router = APIRouter(prefix="/reviews")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_review(
    target_user: int,
    quality: int,
    attitude: int,
    efficiency: int,
    comment: str,
    db: Session = Depends(get_db)
):
    review = Review(
        target_user=target_user,
        score_quality=quality,
        score_attitude=attitude,
        score_efficiency=efficiency,
        comment=comment
    )
    db.add(review)
    db.commit()
    return {"message": "Review submitted"}
