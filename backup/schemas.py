from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# 使用者
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str  # client or contractor

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    class Config:
        orm_mode = True

# 專案
class ProjectBase(BaseModel):
    title: str
    description: str

class ProjectCreate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    id: int
    client_id: int
    assigned_contractor_id: Optional[int]
    status: str
    close_requested: bool
    create_time: datetime
    close_time: Optional[datetime]
    close_explanation: Optional[str]

    class Config:
        orm_mode = True

# 退件說明
class ProjectRejectionBase(BaseModel):
    project_id: int
    explanation: str

class ProjectRejectionCreate(ProjectRejectionBase):
    pass

class ProjectRejectionOut(ProjectRejectionBase):
    id: int
    rejection_date: datetime

    class Config:
        orm_mode = True

# 報價
class BidBase(BaseModel):
    project_id: int
    price: float

class BidCreate(BidBase):
    pass

class BidOut(BidBase):
    id: int
    contractor_id: int
    status: str

    class Config:
        orm_mode = True
