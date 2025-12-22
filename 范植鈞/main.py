from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from auth import router as auth_router, get_current_user, login_user, hash_password
from routers import projects, bids, upload, review
import models
from models import User
import schemas

templates = Jinja2Templates(directory="templates")

app = FastAPI(title="Freelance Platform (Session Only)")
app.include_router(bids.router)
app.include_router(upload.router)
app.include_router(review.router)

app.add_middleware(SessionMiddleware, secret_key="super-secret-session-key")

# 建立資料表
Base.metadata.create_all(bind=engine)

# 註冊路由
app.include_router(auth_router)
app.include_router(projects.router)

# GET 根目錄
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = await get_current_user(request)
    
    flash_message = request.session.pop("flash", None)
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "flash": flash_message})

# GET 登入畫面
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):

    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("login.html", {"request": request, "flash": flash})

# GET 登出
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    request.session["flash"] = "成功登出!"
    return RedirectResponse("/", status_code=302)

# GET 註冊畫面
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})
