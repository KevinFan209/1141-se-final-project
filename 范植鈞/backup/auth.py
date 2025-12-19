from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from database import get_db
import models
from models import User
import schemas

router = APIRouter(prefix="/auth", tags=["Auth"])

templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user

async def login_user(request: Request, username: str, password: str, response: Response):
    db: Session = next(get_db())
    user_obj = db.query(User).filter(User.username == username).first()
    if not user_obj or not pwd_context.verify(password, user_obj.hashed_password):
        return False
    # 將使用者資訊存進 session
    request.session["user"] = {
        "id": user_obj.id,
        "username": user_obj.username,
        "role": user_obj.role
    }
    return True

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

@router.post("/register")
async def register_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), role: str = Form(...), db: Session = Depends(get_db)):
    # 檢查 email 是否已註冊
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email 已被註冊"})
    
    hashed = hash_password(password)
    new_user = models.User(username=username, email=email, hashed_password=hashed, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 註冊完成後直接登入
    request.session["user"] = {"id": new_user.id, "username": new_user.username, "role": new_user.role}
    return RedirectResponse("/", status_code=302)

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    success = await login_user(request, username, password, request)
    if not success:
        return templates.TemplateResponse("login.html", {"request": request, "error": "帳號或密碼錯誤"})
    
    request.session["flash"] = "登入成功!"
    return RedirectResponse("/", status_code=302)

@router.post("/delete_account")
async def delete_account(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登入")
    
    db_user = db.query(models.User).filter(models.User.id == user["id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    
    db.delete(db_user)
    db.commit()
    
    request.session.clear()
    
    return RedirectResponse("/", status_code=302)

@router.get("/me")
def get_me(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {"user": user}