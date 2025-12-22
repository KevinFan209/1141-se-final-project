from flask import Blueprint, request, redirect, url_for, render_template, flash
from flask_login import login_required, current_user
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from datetime import datetime, timedelta

from models import Review, Project, Bid

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/review", tags=["Review"])
REVIEW_DEADLINE_DAYS = 7

def get_user_rating_summary(user_id: int, limit_comments: int = 5):
    """
    回傳：
    - avg_rating：所有收到的 Review 的平均星等（0~5）
    - count：評價數
    - recent_comments：最近 N 則評論（含 reviewer username, avg_score, comment, created_at）
    """
    # 1) 平均分（用三維度平均再取平均）
    avg_expr = (Review.score_1 + Review.score_2 + Review.score_3) / 3.0
    avg_rating = db.session.query(func.avg(avg_expr)).filter(Review.reviewee_id == user_id).scalar()
    count = db.session.query(func.count(Review.id)).filter(Review.reviewee_id == user_id).scalar()

    if avg_rating is None:
        avg_rating = 0.0
    if count is None:
        count = 0

    # 2) 最近評論（只取有 comment 的）
    recent = (Review.query
              .filter(Review.reviewee_id == user_id, Review.comment.isnot(None), Review.comment != "")
              .order_by(Review.created_at.desc())
              .limit(limit_comments)
              .all())

    recent_comments = []
    for r in recent:
        recent_comments.append({
            "reviewer_name": r.reviewer.username if r.reviewer else f"User#{r.reviewer_id}",
            "avg_score": r.avg_score(),
            "comment": r.comment,
            "created_at": r.created_at
        })

    return {
        "avg_rating": float(avg_rating),
        "count": int(count),
        "recent_comments": recent_comments
    }


def can_submit_review(project: Project, reviewer_id: int, reviewee_id: int) -> bool:
    """
    規則：
    - 專案必須 closed
    - reviewer 必須是該專案甲方或乙方之一
    - reviewee 必須是對方
    - 期限內（若設期限）
    - 不可重複評價
    """
    if not project or project.status != 'closed':
        return False

    # 只能是甲乙互評
    valid_pair = (
        (reviewer_id == project.client_id and reviewee_id == project.contractor_id) or
        (reviewer_id == project.contractor_id and reviewee_id == project.client_id)
    )
    if not valid_pair:
        return False

    # 期限：結案後 REVIEW_DEADLINE_DAYS 天內
    REVIEW_DEADLINE_DAYS = 7
    if project.closed_at:
        deadline = project.closed_at + timedelta(days=REVIEW_DEADLINE_DAYS)
        if datetime.utcnow() > deadline:
            return False

    # 防重複
    existing = Review.query.filter_by(
        project_id=project.id,
        reviewer_id=reviewer_id,
        reviewee_id=reviewee_id
    ).first()
    return existing is None


def role_dimensions(role: str):
    """
    回傳該角色被評時，三個維度的文字（符合圖片一）
    """
    if role == "client":
        return ("需求合理性", "驗收難度", "合作態度")
    # ROLE_CONTRACTOR
    return ("產出品質", "執行效率", "合作態度")

# ----------------------
# 工具函式
# ----------------------

def get_user_rating_summary(user_id):
    avg_expr = (Review.score_1 + Review.score_2 + Review.score_3) / 3.0
    avg_rating = db.session.query(func.avg(avg_expr)) \
        .filter(Review.reviewee_id == user_id).scalar() or 0

    count = Review.query.filter_by(reviewee_id=user_id).count()

    comments = Review.query.filter_by(reviewee_id=user_id) \
        .order_by(Review.created_at.desc()).limit(5).all()

    return avg_rating, count, comments


def can_submit_review(project, reviewer_id, reviewee_id):
    if project.status != 'closed':
        return False

    existing = Review.query.filter_by(
        project_id=project.id,
        reviewer_id=reviewer_id,
        reviewee_id=reviewee_id
    ).first()

    return existing is None

@router.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)

    is_client = current_user.id == project.client_id
    is_contractor_assigned = current_user.id == project.contractor_id
    is_contractor_user = current_user.role == "contractor"
    is_open = project.status == 'open'

    if not (is_client or is_contractor_assigned or is_open):
        flash('您沒有權限查看此專案。', 'danger')
        return redirect(url_for('dashboard'))

    proposals = []
    if is_client:
        proposals = Bid.query.filter_by(project_id=project_id).order_by(Bid.submitted_at.desc()).all()

    my_proposal = None
    if is_contractor_user:
        my_proposal = Bid.query.filter_by(project_id=project_id, contractor_id=current_user.id).first()

    # =========================
    # ✅ 圖片一需求：查看對方平均評價 + 質性意見
    # - 乙方看需求 → 看甲方評價（client_rating）
    # - 甲方看提案 → 看各乙方評價（contractor_ratings）
    # =========================

    # 乙方看需求：顯示甲方（委託人）評價摘要
    client_rating = get_user_rating_summary(project.client_id)

    # 甲方看提案：每個 proposal 的 contractor 顯示評價摘要
    contractor_ratings = {}
    if is_client and proposals:
        unique_contractor_ids = list({p.contractor_id for p in proposals})
        for cid in unique_contractor_ids:
            contractor_ratings[cid] = get_user_rating_summary(cid)

    # =========================
    # ✅ 結案後互評：判斷能不能評
    # =========================
    can_review = False
    review_dims = None
    my_existing_review = None

    if project.status == 'closed' and project.contractor_id:
        # 你會評對方
        if current_user.id == project.client_id:
            reviewee_id = project.contractor_id
            reviewee_role = "contractor"
        elif current_user.id == project.contractor_id:
            reviewee_id = project.client_id
            reviewee_role = "client"
        else:
            reviewee_id = None
            reviewee_role = None

        if reviewee_id:
            can_review = can_submit_review(project, current_user.id, reviewee_id)
            review_dims = role_dimensions(reviewee_role)

            my_existing_review = Review.query.filter_by(
                project_id=project.id,
                reviewer_id=current_user.id,
                reviewee_id=reviewee_id
            ).first()

    return render_template(
        'project_detail.html',
        project=project,
        proposals=proposals,
        is_client=is_client,
        is_contractor=is_contractor_user,
        is_contractor_assigned=is_contractor_assigned,
        my_proposal=my_proposal,

        # ✅ 新增給模板用
        client_rating=client_rating,
        contractor_ratings=contractor_ratings,
        can_review=can_review,
        review_dims=review_dims,
        my_existing_review=my_existing_review,
        review_deadline_days=REVIEW_DEADLINE_DAYS
    )


# ----------------------
# 送出評價
# ----------------------

@router.get('/submit_review', response_class=HTMLResponse)
#@login_required
async def submit_review(project_id):
    project = Project.query.get_or_404(project_id)

    # 判斷互評對象
    if current_user.id == project.client_id:
        reviewee_id = project.contractor_id
        reviewee_role = 'contractor'
    else:
        reviewee_id = project.client_id
        reviewee_role = 'client'

    review = Review(
        project_id=project.id,
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        reviewee_role=reviewee_role,
        score_1=int(request.form['score_1']),
        score_2=int(request.form['score_2']),
        score_3=int(request.form['score_3']),
        comment=request.form.get('comment')
    )

    db.session.add(review)
    db.session.commit()

    return templates.TemplateResponse("google.com", {"request": request})
