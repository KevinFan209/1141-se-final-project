from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/bids", tags=["Bids"])

# POST 移除未被選中的承包人
@router.post("/remove")
def remove_rejected_bid(
    bid_id: int = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登入")

    bid = db.query(models.Bid).filter(models.Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="報價不存在")

    if bid.contractor_id != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="無權限刪除此報價")

    if bid.status != "rejected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能刪除被拒絕的報價")

    db.delete(bid)
    db.commit()

    request.session["flash"] = "成功移除！"

    return RedirectResponse(url="/projects/my_bids", status_code=status.HTTP_303_SEE_OTHER)
