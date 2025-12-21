from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):# 使用者屬性
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)# client or conctractor

    # 如果是委託人建立的專案
    client_projects = relationship("Project", back_populates="client", foreign_keys="Project.client_id")

    # 如果是接案人承接的專案
    contractor_projects = relationship("Project", back_populates="contractor", foreign_keys="Project.assigned_contractor_id")

class Project(Base):# 專案屬性
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"))
    assigned_contractor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    status = Column(String, default="open")# open(未承包) or in_process(進行中) or closed(結案) or noBid(不可報價)
    close_requested = Column(Boolean, default=False)# 是否已請求結案

    create_time = Column(DateTime, default=datetime.now)
    close_time = Column(DateTime, nullable=True)
    close_explanation = Column(Text, nullable=True)

    proposal_deadline = Column(DateTime, nullable=False)

    #定義資料表之間的關係
    client = relationship("User", foreign_keys=[client_id])
    contractor = relationship("User", foreign_keys=[assigned_contractor_id])
    bids = relationship("Bid", back_populates="project")
    rejections = relationship("ProjectRejection", back_populates="project", order_by="ProjectRejection.rejection_date.desc()")

class ProjectRejection(Base):
    __tablename__ = "project_rejections"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    rejection_date = Column(DateTime, default=datetime.now)
    explanation = Column(Text)

    #定義資料表之間的關係
    project = relationship("Project", back_populates="rejections")

class Bid(Base):
    __tablename__ = "bids"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    contractor_id = Column(Integer, ForeignKey("users.id"))
    price = Column(Float, nullable=False)
    proposal_file = Column(String, nullable=True)
    status = Column(String, default="pending")# pending(接受報價) or accept(同意報價) or rejected(拒絕報價)

    #定義資料表之間的關係
    project = relationship("Project", back_populates="bids")
    contractor = relationship("User")

class Intents(Base): #from 王茂綸 
    __tablename__ = "intents"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String(50), unique=True, nullable=False)
    quote = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    attachments = Column()
    created_at = Column(DateTime, default=datetime.now)

class Issues(Base): #from 王茂綸
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    issue_is_opened = Column(Boolean, nullable=False)
    create_by =  Column(Integer, ForeignKey("users.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    resolve_at = Column(DateTime, default=datetime.now)

class Issues_comments(Base): #from 王茂綸
    __tablename__ = "issues_comments"
    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class Replies(Base): #from 王茂綸
    __tablename__ = "replies"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, unique=True)
    responder_id = Column(Integer, unique=True)
    price_text = Column(String(100), nullable=False)
    message = Column(Text)
    attachments = Column()
    status = Column(String(30))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)