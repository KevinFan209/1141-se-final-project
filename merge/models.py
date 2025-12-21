from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    role = Column(String)  # client / worker

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(Text)
    deadline = Column(DateTime)
    owner_id = Column(Integer, ForeignKey("users.id"))
    finished = Column(Boolean, default=False)

class Bid(Base):
    __tablename__ = "bids"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    price = Column(Integer)
    proposal_file = Column(String)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    target_user = Column(Integer, ForeignKey("users.id"))
    score_quality = Column(Integer)
    score_attitude = Column(Integer)
    score_efficiency = Column(Integer)
    comment = Column(Text)

class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String)
    content = Column(Text)
    closed = Column(Boolean, default=False)

class IssueReply(Base):
    __tablename__ = "issue_replies"
    id = Column(Integer, primary_key=True)
    issue_id = Column(Integer, ForeignKey("issues.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
