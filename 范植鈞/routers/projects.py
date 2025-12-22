from fastapi import APIRouter, Depends, Request, HTTPException, Form, status, Query, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
import models
import schemas
from auth import get_current_user
from urllib.parse import quote
from datetime import datetime
import shutil
import os
import zipfile
import io

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/projects", tags=["Projects"])

# GET 建立專案頁面
@router.get("/create_page", response_class=HTMLResponse)
async def create_project_page(request: Request):
    return templates.TemplateResponse("create_project.html", {"request": request})

# POST 建立專案資料(委託人)
@router.post("/create", response_model=schemas.ProjectOut)
def create_project(
        title: str = Form(...), 
        description: str = Form(...), 
        proposal_deadline: str = Form(...),
        request: Request = None, 
        db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user or user["role"] != "client":
        raise HTTPException(status_code=403, detail="無權限建立專案")
    deadline = datetime.strptime(proposal_deadline, "%Y-%m-%dT%H:%M")
    new_project = models.Project(
        title=title,
        description=description,
        client_id=user["id"],
        proposal_deadline=deadline
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    request.session["flash"] = "專案建立成功！"
    return RedirectResponse(url="/", status_code=302)

# POST 報價資訊
@router.post("/bid", response_model=schemas.BidOut)
async def submit_bid(
        project_id: int = Form(...), 
        price: float = Form(...), 
        file: UploadFile = None,
        request: Request = None, 
        db: Session = Depends(get_db),):
    user = request.session.get("user")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    project_title = project.title
    if not user or user["role"] != "contractor":
        raise HTTPException(status_code=403, detail="無權限報價")
    
    # 檢查是否已經對這個專案報價過
    existing_bid = db.query(models.Bid).filter(
        models.Bid.project_id == project_id,
        models.Bid.contractor_id == user["id"]
    ).first()
    if existing_bid:
        raise HTTPException(status_code=400, detail="你已經對此專案報價過，不能再次提交")
    
    proposal_path = f"upload_proposal/{project_title}/{user["username"]}/{file.filename}"
    os.makedirs(proposal_path, exist_ok=True)

    # 儲存檔案
    file_path = os.path.join(proposal_path, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    new_bid = models.Bid(project_id=project_id, contractor_id=user["id"], price=price, proposal_file=proposal_path)
    db.add(new_bid)
    db.commit()
    db.refresh(new_bid)

    request.session["flash"] = "報價成功！"
    return RedirectResponse(url="/projects/my_bids", status_code=302)

# GET 可承接專案列表(接案人)
@router.get("/available_page", response_class=HTMLResponse)
async def available_projects_page(request: Request, db: Session = Depends(get_db)):
    now = datetime.now()
    user = request.session.get("user")
    projects = db.query(models.Project).filter(models.Project.status=="open").all()
    review = db.query(models.Review).all()

    for project in projects:
        if project.proposal_deadline and (now > project.proposal_deadline):
            project.status = "noBid"
            db.commit()            
            
    return templates.TemplateResponse("list_projects.html", {"request": request, "projects": projects, "user": user, "review": review})

# GET 專案列表(委託人)
@router.get("/my_projects", response_class=HTMLResponse)
async def my_projects_page(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    projects = db.query(models.Project).filter(models.Project.client_id==user["id"]).all()
    flash = request.session.pop("flash", None)

    return templates.TemplateResponse("list_projects.html", {"request": request, "projects": projects, "user": user, "flash": flash})

# GET 承包專案(接案人)
@router.get("/my_bids", response_class=HTMLResponse)
async def my_bids_page(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    bids = db.query(models.Bid).filter(models.Bid.contractor_id==user["id"]).all()
    flash = request.session.pop("flash", None)

    return templates.TemplateResponse("list_projects.html", {"request": request, "projects": [b.project for b in bids], "user": user, "flash": flash})

# POST 被選接案人資訊
@router.post("/assign")
def assign_contractor(project_id: int = Form(...), contractor_id: int = Form(...), request: Request = None, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登入")

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="專案不存在")

    if project.client_id != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="無權限操作此專案")

    if project.assigned_contractor_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此專案已指派接案人")

    # 更新專案狀態與指派接案人
    project.assigned_contractor_id = contractor_id
    project.status = "in_process"

    # 接受被選中者，拒絕其他人
    bids = db.query(models.Bid).filter(models.Bid.project_id == project_id).all()
    for bid in bids:
        if bid.contractor_id == contractor_id:
            bid.status = "accepted"
        else:
            bid.status = "rejected"

    db.commit()

    request.session["flash"] = "已選擇接案人!"

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    return RedirectResponse(url=f"/projects/my_projects", status_code=303)

# GET 管理專案(委託人)
@router.get("/manage_client/{project_id}", response_class=HTMLResponse)
async def manage_project_client(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    if project.client_id != user["id"]:
        raise HTTPException(status_code=403, detail="無權限檢視此頁面")
    
    flash = request.session.pop("flash", None)

    base_dir = os.path.join("upload_file", project.title)
    
    # 讀進度檔案資料夾與裡面檔案
    in_process_dir = os.path.join(base_dir, "in_process")
    in_process_data = {}
    if os.path.exists(in_process_dir):
        for date_folder in os.listdir(in_process_dir):
            folder_path = os.path.join(in_process_dir, date_folder)
            if os.path.isdir(folder_path):
                files = [f for f in os.listdir(folder_path) if not f.startswith('.')]
                in_process_data[date_folder] = files

    # 讀結案檔案資料夾與裡面檔案
    final_dir = os.path.join(base_dir, "final")
    final_data = {}
    if os.path.exists(final_dir):
        for date_folder in os.listdir(final_dir):
            folder_path = os.path.join(final_dir, date_folder)
            if os.path.isdir(folder_path):
                files = [f for f in os.listdir(folder_path) if not f.startswith('.')]
                final_data[date_folder] = files

    return templates.TemplateResponse("manage_client.html", {
        "request": request,
        "project": project,
        "in_process_data": in_process_data,
        "final_data": final_data,
        "user": user,
        "flash": flash
        }
    )

# GET 專案管理(接案人)
@router.get("/manage_contractor/{project_id}", response_class=HTMLResponse)
async def manage_contractor_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="請先登入")

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    if project.assigned_contractor_id != user["id"]:
        raise HTTPException(status_code=403, detail="無權限檢視此頁面")
    
    flash = request.session.pop("flash", None)

    base_dir = os.path.join("upload_file", project.title)

    latest_rejection = db.query(models.ProjectRejection).filter(models.ProjectRejection.project_id == project_id).order_by(models.ProjectRejection.rejection_date.desc()).first()
    
    # 讀進度檔案資料夾與裡面檔案
    in_process_dir = os.path.join(base_dir, "in_process")
    in_process_data = {}
    if os.path.exists(in_process_dir):
        for date_folder in os.listdir(in_process_dir):
            folder_path = os.path.join(in_process_dir, date_folder)
            if os.path.isdir(folder_path):
                files = [f for f in os.listdir(folder_path) if not f.startswith('.')]
                in_process_data[date_folder] = files

    # 讀結案檔案資料夾與裡面檔案
    final_dir = os.path.join(base_dir, "final")
    final_data = {}
    if os.path.exists(final_dir):
        for date_folder in os.listdir(final_dir):
            folder_path = os.path.join(final_dir, date_folder)
            if os.path.isdir(folder_path):
                files = [f for f in os.listdir(folder_path) if not f.startswith('.')]
                final_data[date_folder] = files

    return templates.TemplateResponse("manage_contractor.html", {
        "request": request,
        "project": project,
        "in_process_data": in_process_data,
        "final_data": final_data,
        "user": user,
        "latest_rejection": latest_rejection,
        "flash": flash
        }
    )

# GET 下載並打包成zip
@router.get("/download_zip")
def download_zip(project_title: str, folder: str, stage: str = "in_process"):
    base_path = f"upload_file/{project_title}/{stage}/{folder}"
    if not os.path.exists(base_path):
        print(base_path)
        raise HTTPException(status_code=404, detail="檔案不存在")

    # 將資料夾打包成 zip
    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(base_path):
            for file in files:
                file_path = os.path.join(root, file)
                # 加入 zip 時，讓路徑相對於 base_path
                zf.write(file_path, arcname=os.path.relpath(file_path, base_path))
    zip_stream.seek(0)

    # 支援中文檔名
    zip_filename = f"{folder}_{project_title}_{stage}.zip"
    encoded_filename = quote(zip_filename)

    return StreamingResponse(
        zip_stream,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )

@router.get("/proposal_download_zip")
def download_zip(path):
    base_path = path
    if not os.path.exists(base_path):
        print(base_path)
        raise HTTPException(status_code=404, detail="檔案不存在")

    # 將資料夾打包成 zip
    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(base_path):
            for file in files:
                file_path = os.path.join(root, file)
                # 加入 zip 時，讓路徑相對於 base_path
                zf.write(file_path, arcname=os.path.relpath(file_path, base_path))
    zip_stream.seek(0)

    # 支援中文檔名
    zip_filename = f"{base_path}.zip"
    encoded_filename = quote(zip_filename).replace("upload_", "")

    return StreamingResponse(
        zip_stream,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )

# POST 專案狀態
@router.post("/request_close/{project_id}")
def request_close(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="未登入")

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    if project.assigned_contractor_id != user["id"]:
        raise HTTPException(status_code=403, detail="無權限")

    # 更新狀態
    project.close_requested = True
    project.status = "request_close"
    db.commit()

    request.session["flash"] = "請求成功!"

    return RedirectResponse(url=f"/projects/manage_contractor/{project_id}", status_code=303)

# POST 刪除專案
@router.post("/delete/{project_id}")
def delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=403, detail="未登入")
    
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    if project.client_id != user["id"]:
        raise HTTPException(status_code=403, detail="您沒有權限刪除這個專案")
    
    db.query(models.Bid).filter(models.Bid.project_id == project_id).delete()
    
    db.delete(project)
    db.commit()
    if os.path.exists(f"upload_proposal/{project.title}"):
        os.remove(f"upload_proposal/{project.title}")
    request.session["flash"] = "成功刪除專案!"

    return RedirectResponse(url="/projects/my_projects", status_code=302)

# GET 審核頁面
@router.get("/decision/{project_id}")
async def decision_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return templates.TemplateResponse("project_decision.html", {"request": request, "project": project})

# POST 審核結果
@router.post("/decision")
async def submit_decision(
    request: Request,
    project_id: int = Form(...),
    decision: str = Form(...),
    explanation: str = Form(...),
    db: Session = Depends(get_db)
):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="未登入")

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    if project.client_id != user["id"]:
        raise HTTPException(status_code=403, detail="無權限操作")

    if decision == "close":
        project.status = "closed"
        project.close_explanation = explanation
        project.close_time = datetime.now()
        project.close_requested = False
        db.commit()
        request.session["flash"] = "成功送出! 已結案"
    elif decision == "reject":
        project.close_requested = False
        project.status = "in_process"     
        rejection = models.ProjectRejection(
            project_id=project.id,
            rejection_date=datetime.now(),
            explanation=explanation
        )
        db.add(rejection)
        db.commit()
        request.session["flash"] = "成功送出! 已退件"
        move_latest_final_to_rejected(project.title)
    else:
        raise HTTPException(status_code=400, detail="無效的操作")

    return RedirectResponse(url=f"/projects/manage_client/{project.id}", status_code=303)

#定義一個函數，移動被退件的資料夾
def move_latest_final_to_rejected(project_title: str):
    base_dir = os.path.join("upload_file", project_title)
    final_dir = os.path.join(base_dir, "final")
    rejected_dir = os.path.join(base_dir, "rejected")

    os.makedirs(base_dir, exist_ok=True)

    # 取得所有日期資料夾（排除 'rejected'）
    date_folders = [
        f for f in os.listdir(final_dir)
        if os.path.isdir(os.path.join(final_dir, f)) and f != "rejected"
    ]

    if not date_folders:
        return False

    # 找出最新上傳的結案資料夾（依照字母排序或日期格式）
    latest_folder = max(date_folders)
    src_path = os.path.join(final_dir, latest_folder)
    dest_path = os.path.join(rejected_dir, latest_folder)

    # 移動資料夾（含檔案）
    shutil.move(src_path, dest_path)

    return True