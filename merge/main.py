from fastapi import FastAPI
from database import engine
from models import Base
from routers import issue, review, bid

app = FastAPI(title="委託接案平台")

Base.metadata.create_all(bind=engine)

app.include_router(issue.router)
app.include_router(review.router)
app.include_router(bid.router)

@app.get("/")
def root():
    return {"status": "Server running"}
