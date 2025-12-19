from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# 角色定義
ROLE_CLIENT = 'client'          # 委託人
ROLE_CONTRACTOR = 'contractor'  # 接案人

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # 專案狀態: 'open', 'pending', 'waiting_review', 'closed', 'rejected'
    status = db.Column(db.String(20), default='open', nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ 用來做「評價期限」判斷：結案時間
    closed_at = db.Column(db.DateTime, nullable=True)

    # 結案檔案路徑
    delivery_file_path = db.Column(db.String(255), nullable=True)

    # 外鍵定義
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contractor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # 關聯定義
    client = db.relationship(
        'User',
        foreign_keys=[client_id],
        backref=db.backref('projects_created', lazy=True)
    )

    contractor = db.relationship(
        'User',
        foreign_keys=[contractor_id],
        backref=db.backref('projects_contracted', lazy=True)
    )

    proposals = db.relationship(
        'Proposal',
        backref='project',
        lazy=True,
        cascade='all, delete-orphan'
    )

    # ✅ 該專案的評價（互評最多兩筆）
    reviews = db.relationship(
        'Review',
        backref='project',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Project {self.title} (Status: {self.status})>'


class Proposal(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    price = db.Column(db.Float, nullable=False)
    details = db.Column(db.Text, nullable=False)

    # 提案狀態: 'submitted', 'accepted', 'rejected'
    status = db.Column(db.String(20), default='submitted', nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    contractor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    contractor = db.relationship('User', backref=db.backref('proposals', lazy=True))

    def __repr__(self):
        return f'<Proposal ID:{self.id} for Project:{self.project_id} by User:{self.contractor_id}>'


# =========================
# ✅ 新增：評價機制 Review
# =========================
class Review(db.Model):
    """
    圖片一需求：
    - 結案後互評
    - 三維度 1~5 星 + 質性評論
    - 可查平均評價與質性意見
    """
    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # 被評者角色：client / contractor（決定三維度文字要顯示哪一套）
    reviewee_role = db.Column(db.String(20), nullable=False)

    # 三維度星等 1~5
    score_1 = db.Column(db.Integer, nullable=False)
    score_2 = db.Column(db.Integer, nullable=False)
    score_3 = db.Column(db.Integer, nullable=False)

    # 質性意見
    comment = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref=db.backref('reviews_given', lazy=True))
    reviewee = db.relationship('User', foreign_keys=[reviewee_id], backref=db.backref('reviews_received', lazy=True))

    __table_args__ = (
        # ✅ 防止同一專案對同一對象重複評價
        db.UniqueConstraint('project_id', 'reviewer_id', 'reviewee_id', name='uq_review_once_per_pair'),
    )

    def avg_score(self) -> float:
        return (self.score_1 + self.score_2 + self.score_3) / 3.0

    def __repr__(self):
        return f'<Review {self.id} P{self.project_id} {self.reviewer_id}->{self.reviewee_id}>'
