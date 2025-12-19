from flask import Flask, render_template, redirect, url_for, flash, request, abort, send_from_directory
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from models import db, User, ROLE_CLIENT, ROLE_CONTRACTOR, Project, Proposal, Review
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func

# 檔案上傳配置
UPLOAD_FOLDER = 'project_deliveries'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key_FINAL_VERSION_2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ 評價期限（結案後幾天內可互評）
REVIEW_DEADLINE_DAYS = 7

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '請登入以存取此頁面。'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Jinja2 過濾器：用於在模板中處理 None 值 ---
def ternary_filter(value, true_value, false_value, default=None):
    if value is None and default is not None:
        return default
    return true_value if value else false_value

app.jinja_env.filters['ternary'] = ternary_filter
# --------------------

# --- 初始化資料庫 ---
with app.app_context():
    db.create_all()
    print("Database initialization check complete.")
# --------------------


# =========================
# ✅ 評價工具函式（平均評分＋最近評論）
# =========================
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
    if role == ROLE_CLIENT:
        return ("需求合理性", "驗收難度", "合作態度")
    # ROLE_CONTRACTOR
    return ("產出品質", "執行效率", "合作態度")


# --------------------
# 路由定義 (Routes)
# --------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        if not (role == ROLE_CLIENT or role == ROLE_CONTRACTOR):
            flash('請選擇有效的角色。', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('該使用者名稱已被註冊！', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('註冊成功，請登入！', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('登入成功！', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('使用者名稱或密碼錯誤。', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已登出。', 'info')
    return redirect(url_for('login'))


@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == ROLE_CLIENT:
        return redirect(url_for('client_dashboard'))
    elif current_user.role == ROLE_CONTRACTOR:
        return redirect(url_for('contractor_dashboard'))
    flash('您的角色未被識別。', 'warning')
    return redirect(url_for('logout'))


# --- 委託人儀表板 (Client Dashboard) ---
@app.route('/client')
@login_required
def client_dashboard():
    if current_user.role != ROLE_CLIENT:
        flash('您沒有權限存取此頁面。', 'warning')
        return redirect(url_for('dashboard'))

    active_projects = Project.query.filter(
        (Project.client_id == current_user.id) &
        (Project.status.in_(['open', 'pending', 'waiting_review']))
    ).order_by(Project.created_at.desc()).all()

    historical_projects = Project.query.filter(
        (Project.client_id == current_user.id) &
        (Project.status.in_(['closed', 'rejected']))
    ).order_by(Project.created_at.desc()).all()

    return render_template(
        'client_dashboard.html',
        projects=active_projects,
        historical_projects=historical_projects
    )


@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    if current_user.role != ROLE_CLIENT:
        flash('只有委託人可以建立專案。', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        if not title or not description:
            flash('專案標題和描述皆不可為空！', 'danger')
            return render_template('create_project.html')

        new_project = Project(
            title=title,
            description=description,
            client_id=current_user.id,
            status='open'
        )
        db.session.add(new_project)
        db.session.commit()

        flash(f'專案 "{title}" 已成功發布！', 'success')
        return redirect(url_for('client_dashboard'))
    return render_template('create_project.html')


@app.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if current_user.role != ROLE_CLIENT or project.client_id != current_user.id or project.status != 'open':
        flash('您沒有權限修改此專案，或專案已開始進行。', 'danger')
        return redirect(url_for('project_detail', project_id=project.id))

    if request.method == 'POST':
        project.title = request.form.get('title')
        project.description = request.form.get('description')
        try:
            db.session.commit()
            flash('專案資訊更新成功！', 'success')
        except Exception:
            db.session.rollback()
            flash('專案更新失敗。', 'danger')
        return redirect(url_for('client_dashboard'))

    return render_template('edit_project.html', project=project)


@app.route('/accept_proposal/<int:proposal_id>', methods=['POST'])
@login_required
def accept_proposal(proposal_id):
    proposal = Proposal.query.get_or_404(proposal_id)
    project = proposal.project

    if current_user.role != ROLE_CLIENT or project.client_id != current_user.id or project.status != 'open':
        flash('您沒有權限執行此操作。', 'danger')
        return redirect(url_for('project_detail', project_id=project.id))

    try:
        proposal.status = 'accepted'
        project.status = 'pending'
        project.contractor_id = proposal.contractor_id

        Proposal.query.filter(
            (Proposal.project_id == project.id) &
            (Proposal.id != proposal_id)
        ).update({'status': 'rejected'}, synchronize_session=False)

        db.session.commit()
        flash(f'已接受 {proposal.contractor.username} 的報價，專案狀態變為進行中。', 'success')
    except Exception:
        db.session.rollback()
        flash('接受報價操作失敗。', 'danger')

    return redirect(url_for('project_detail', project_id=project.id))


@app.route('/review_delivery/<int:project_id>', methods=['POST'])
@login_required
def review_delivery(project_id):
    project = Project.query.get_or_404(project_id)
    action = request.form.get('action')  # 'accept' or 'reject'

    if current_user.role != ROLE_CLIENT or project.client_id != current_user.id or project.status != 'waiting_review':
        flash('您沒有權限或專案狀態不允許此操作。', 'danger')
        return redirect(url_for('project_detail', project_id=project.id))

    try:
        if action == 'accept':
            project.status = 'closed'
            # ✅ 記錄結案時間（供評價期限）
            project.closed_at = datetime.utcnow()
            flash('結案成功，報酬已確認撥款給接案人。', 'success')
        elif action == 'reject':
            project.status = 'pending'
            flash('已退回結案檔案，請通知接案人修正。', 'warning')
        else:
            flash('無效的操作。', 'danger')
            return redirect(url_for('project_detail', project_id=project.id))

        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('執行結案操作失敗。', 'danger')

    return redirect(url_for('project_detail', project_id=project.id))


# --- 接案人儀表板 (Contractor Dashboard) ---
@app.route('/contractor')
@login_required
def contractor_dashboard():
    if current_user.role != ROLE_CONTRACTOR:
        flash('您沒有權限存取此頁面。', 'warning')
        return redirect(url_for('dashboard'))

    in_progress_projects = Project.query.filter(
        (Project.contractor_id == current_user.id) &
        (Project.status.in_(['pending', 'waiting_review']))
    ).order_by(Project.created_at.desc()).all()

    open_projects = Project.query.filter(Project.status == 'open').order_by(Project.created_at.desc()).all()

    historical_projects = Project.query.filter(
        (Project.contractor_id == current_user.id) &
        (Project.status.in_(['closed', 'rejected']))
    ).order_by(Project.created_at.desc()).all()

    return render_template(
        'contractor_dashboard.html',
        in_progress_projects=in_progress_projects,
        open_projects=open_projects,
        historical_projects=historical_projects
    )


@app.route('/make_proposal/<int:project_id>', methods=['POST'])
@login_required
def make_proposal(project_id):
    if current_user.role != ROLE_CONTRACTOR:
        abort(403)
    project = Project.query.get_or_404(project_id)

    if project.status != 'open':
        flash('此專案目前不接受報價。', 'danger')
        return redirect(url_for('project_detail', project_id=project_id))

    existing_proposal = Proposal.query.filter_by(project_id=project_id, contractor_id=current_user.id).first()
    if existing_proposal:
        flash('您已對此專案提出報價。', 'warning')
        return redirect(url_for('project_detail', project_id=project_id))

    try:
        price = float(request.form.get('price'))
        details = request.form.get('details')
        if price <= 0 or not details:
            flash('報價金額必須大於零，且細節不可為空。', 'danger')
            return redirect(url_for('project_detail', project_id=project_id))

        new_proposal = Proposal(
            price=price,
            details=details,
            project_id=project_id,
            contractor_id=current_user.id
        )
        db.session.add(new_proposal)
        db.session.commit()
        flash('報價已成功提交！', 'success')
    except ValueError:
        flash('報價金額必須是有效的數字。', 'danger')
    except Exception:
        db.session.rollback()
        flash('提交報價失敗。', 'danger')

    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/submit_delivery/<int:project_id>', methods=['POST'])
@login_required
def submit_delivery(project_id):
    if current_user.role != ROLE_CONTRACTOR:
        abort(403)
    project = Project.query.get_or_404(project_id)

    if project.contractor_id != current_user.id or project.status != 'pending':
        flash('您沒有權限提交此專案的結案，或專案狀態不正確。', 'danger')
        return redirect(url_for('project_detail', project_id=project_id))

    if 'file' not in request.files:
        flash('未選擇檔案。', 'danger')
        return redirect(url_for('project_detail', project_id=project_id))

    file = request.files['file']
    if file.filename == '':
        flash('未選擇檔案。', 'danger')
        return redirect(url_for('project_detail', project_id=project_id))

    if file:
        try:
            filename = secure_filename(file.filename)
            unique_filename = f"{project.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)

            project.delivery_file_path = unique_filename
            project.status = 'waiting_review'
            db.session.commit()
            flash('結案檔案已成功提交，等待委託人審核。', 'success')
        except Exception:
            db.session.rollback()
            flash('檔案上傳或資料庫更新失敗。', 'danger')

    return redirect(url_for('project_detail', project_id=project.id))


@app.route('/download_delivery/<path:filename>')
@login_required
def download_delivery(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)


# =========================
# ✅ 新增：送出評價
# =========================
@app.route('/submit_review/<int:project_id>', methods=['POST'])
@login_required
def submit_review(project_id):
    project = Project.query.get_or_404(project_id)

    # 只有專案甲乙能評
    if current_user.id not in [project.client_id, project.contractor_id]:
        flash('您沒有權限評價此專案。', 'danger')
        return redirect(url_for('project_detail', project_id=project_id))

    # 判斷你要評誰（固定評對方）
    if current_user.id == project.client_id:
        reviewee_id = project.contractor_id
        reviewee_role = ROLE_CONTRACTOR
    else:
        reviewee_id = project.client_id
        reviewee_role = ROLE_CLIENT

    if not reviewee_id:
        flash('專案尚未指派合作對象，無法評價。', 'warning')
        return redirect(url_for('project_detail', project_id=project_id))

    if not can_submit_review(project, current_user.id, reviewee_id):
        flash('目前無法送出評價（可能未結案、已超過期限、或已評價過）。', 'warning')
        return redirect(url_for('project_detail', project_id=project_id))

    # 讀取星等（1~5）
    try:
        s1 = int(request.form.get('score_1', 0))
        s2 = int(request.form.get('score_2', 0))
        s3 = int(request.form.get('score_3', 0))
        comment = (request.form.get('comment') or "").strip()

        for s in [s1, s2, s3]:
            if s < 1 or s > 5:
                raise ValueError("Score out of range")

        new_review = Review(
            project_id=project.id,
            reviewer_id=current_user.id,
            reviewee_id=reviewee_id,
            reviewee_role=reviewee_role,
            score_1=s1,
            score_2=s2,
            score_3=s3,
            comment=comment
        )
        db.session.add(new_review)
        db.session.commit()
        flash('評價已成功送出！', 'success')
    except Exception:
        db.session.rollback()
        flash('評價送出失敗（請確認星等 1~5）。', 'danger')

    return redirect(url_for('project_detail', project_id=project_id))


# --- 專案詳情頁 (Project Detail) ---
@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)

    is_client = current_user.id == project.client_id
    is_contractor_assigned = current_user.id == project.contractor_id
    is_contractor_user = current_user.role == ROLE_CONTRACTOR
    is_open = project.status == 'open'

    if not (is_client or is_contractor_assigned or is_open):
        flash('您沒有權限查看此專案。', 'danger')
        return redirect(url_for('dashboard'))

    proposals = []
    if is_client:
        proposals = Proposal.query.filter_by(project_id=project_id).order_by(Proposal.submitted_at.desc()).all()

    my_proposal = None
    if is_contractor_user:
        my_proposal = Proposal.query.filter_by(project_id=project_id, contractor_id=current_user.id).first()

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
            reviewee_role = ROLE_CONTRACTOR
        elif current_user.id == project.contractor_id:
            reviewee_id = project.client_id
            reviewee_role = ROLE_CLIENT
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


if __name__ == '__main__':
    print("應用程式啟動中...")
    print("請在瀏覽器中開啟: http://127.0.0.1:5000")
    app.run(debug=True)
