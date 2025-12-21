from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Issue, IssueReply

router = APIRouter(prefix="/issues")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_issue(project_id: int, title: str, content: str, db: Session = Depends(get_db)):
    issue = Issue(project_id=project_id, title=title, content=content)
    db.add(issue)
    db.commit()
    return {"message": "Issue created"}

@router.post("/{issue_id}/reply")
def reply_issue(issue_id: int, content: str, db: Session = Depends(get_db)):
    reply = IssueReply(issue_id=issue_id, content=content)
    db.add(reply)
    db.commit()
    return {"message": "Reply added"}

@router.post("/{issue_id}/close")
def close_issue(issue_id: int, db: Session = Depends(get_db)):
    issue = db.query(Issue).get(issue_id)
    issue.closed = True
    db.commit()
    return {"message": "Issue closed"}
