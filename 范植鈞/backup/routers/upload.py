from fastapi import APIRouter, UploadFile, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
import os
from datetime import datetime

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/upload", tags=["Upload"])

#POST 上傳進度檔案
@router.post("/file")
async def upload_project_file(
    request: Request,
    project_id: int = Form(...),
    description: str = Form(""),
    file: UploadFile = None,
    db: Session = Depends(get_db)
):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="未登入")

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    # 建立路徑：upload_file/{project.title}/in_process/{日期}/
    in_process_path = f"upload_file/{project.title}/in_process/{datetime.now().strftime("%Y-%m-%d_%H-%M")}"
    os.makedirs(in_process_path, exist_ok=True)

    # 儲存檔案
    file_path = os.path.join(in_process_path, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    request.session["flash"] = "已上傳檔案!"

    return RedirectResponse(url=f"/upload/upload_project/{project.id}", status_code=303)

# POST 上傳結案檔案
@router.post("/final")
async def upload_final_file(
    request: Request,
    project_id: int = Form(...),
    description: str = Form(""),
    file: UploadFile = None,
    db: Session = Depends(get_db)
):    
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="未登入")

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    
    final_path = f"upload_file/{project.title}/final/{datetime.now().strftime("%Y-%m-%d_%H-%M")}"
    os.makedirs(final_path, exist_ok=True)

    file_path = os.path.join(final_path, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    request.session["flash"] = "已上傳結案檔案!按下 '請求結案' 按鈕通知委託人"    

    return RedirectResponse(url=f"/projects/manage_contractor/{project.id}", status_code=303)

# GET 上傳頁面
@router.get("/upload_project/{project_id}", response_class=HTMLResponse)
async def manage_project_contractor(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    # 確認只有承包人可看
    if project.contractor.id != user["id"]:
        raise HTTPException(status_code=403, detail="無權限檢視此頁面")
    
    if project.status == "closed":
        raise HTTPException(status_code=403, detail="專案已結案，無法上傳")
    
    flash = request.session.pop("flash", None)

    return templates.TemplateResponse("upload_project.html", {"request": request, "project": project, "user": user, "flash": flash})
