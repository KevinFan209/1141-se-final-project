<?php
// 啟動 Session (必須在任何輸出之前)
session_start();

// ====================================================================
// 1. 設定與工具函式 (Helper Functions)
// ====================================================================

// 設置 Headers
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With');
header('Content-Type: application/json; charset=utf-8');

// 處理 OPTIONS 預檢請求
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    http_response_code(200);
    exit();
}

/**
 * 發送 JSON 響應並終止腳本執行
 * @param array $data 要輸出的資料
 * @param int $statusCode HTTP 狀態碼
 */
function sendJson(array $data, int $statusCode = 200)
{
    http_response_code($statusCode);
    echo json_encode($data);
    exit();
}

/**
 * 從 Session 中獲取當前登入使用者 ID
 * @return int 使用者 ID，如果未登入則為 0
 */
function getCurrentUserId(): int
{
    // 假設你在登入時將 user_id 存入 $_SESSION['user_id']
    if (isset($_SESSION['user_id']) && is_numeric($_SESSION['user_id'])) {
        return (int) $_SESSION['user_id'];
    }
    return 0;
}


// ====================================================================
// 2. 資料庫連線
// ====================================================================

// **請確認修改以下設定為你的資料庫參數**
$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

try {
    $pdo = new PDO("pgsql:host=$dbHost;dbname=$dbName", $dbUser, $dbPass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->exec("SET TIMEZONE='Asia/Taipei'");
} catch (PDOException $e) {
    sendJson(['success' => false, 'message' => '資料庫連線失敗，請檢查設定。'], 500);
}


// ====================================================================
// 3. 具體 API 邏輯實作 (Handle Functions)
//    - 所有函式定義放在這裡，確保在路由前被載入。
// ====================================================================

// 3.1. 獲取事項列表 (GET /issue.php?action=issues/list)
function handleFetchIssues(PDO $pdo): void
{
    $projectId = $_GET['project_id'] ?? null;
    if (!$projectId) {
        sendJson(['success' => false, 'message' => '缺少 project_id 參數'], 400);
    }

    $sql = "SELECT id, title, description, issue_is_opened, created_at FROM issues 
            WHERE project_id = :project_id 
            ORDER BY issue_is_opened DESC, created_at DESC";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([':project_id' => $projectId]);
    $issues = $stmt->fetchAll(PDO::FETCH_ASSOC);

    sendJson(['success' => true, 'issues' => $issues]);
}

// 3.2. 新增事項 (POST /issue.php?action=issues/create)
function handleCreateIssue(PDO $pdo): void
{
    $projectId = $_POST['project_id'] ?? null;
    $title = $_POST['title'] ?? null;
    $createdBy = getCurrentUserId();

    if ($createdBy === 0) {
        sendJson(['success' => false, 'message' => '請先登入，無法建立事項'], 401);
    }
    if (!$projectId || !$title) {
        sendJson(['success' => false, 'message' => '缺少 project_id 或 title 參數'], 400);
    }

    try {
        $sql = "INSERT INTO issues (project_id, title, created_by) 
                VALUES (:project_id, :title, :created_by) RETURNING id, created_at";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            ':project_id' => $projectId,
            ':title' => $title,
            ':created_by' => $createdBy
        ]);

        $newIssue = $stmt->fetch(PDO::FETCH_ASSOC);

        sendJson([
            'success' => true,
            'message' => '事項新增成功',
            'issue_id' => $newIssue['id'],
            'created_at' => $newIssue['created_at']
        ]);

    } catch (PDOException $e) {
        sendJson(['success' => false, 'message' => '新增失敗，請檢查 project_id 是否有效。'], 500);
    }
}

// 3.3. 解決事項 (POST /issue.php?action=issues/resolve)
function handleResolveIssue(PDO $pdo): void
{
    $issueId = $_POST['issue_id'] ?? null;
    if (!$issueId) {
        sendJson(['success' => false, 'message' => '缺少 issue_id 參數'], 400);
    }

    try {
        // SQL 範例
        $sql = "UPDATE issues SET issue_is_opened = FALSE, resolved_at = NOW() 
        WHERE id = :id AND created_by = :user_id AND issue_is_opened = TRUE";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([':id' => $issueId, ':user_id' => getCurrentUserId()]);

        if ($stmt->rowCount() > 0) {
            sendJson(['success' => true, 'message' => '事項已解決']);
        } else {
            sendJson(['success' => false, 'message' => '事項不存在或已被解決']);
        }
    } catch (PDOException $e) {
        sendJson(['success' => false, 'message' => '更新失敗。'], 500);
    }
}

// 3.4. 獲取留言 (GET /issue.php?action=issues/comments)
function handleFetchComments(PDO $pdo): void
{
    $issueId = $_GET['issue_id'] ?? null;
    if (!$issueId) {
        sendJson(['success' => false, 'message' => '缺少 issue_id 參數'], 400);
    }

    // 備註：你需要有一個 'users' 資料表，其中包含 'username' 欄位。
    $sql = "SELECT 
                c.id, 
                c.user_id, 
                c.content, 
                c.created_at,
                u.username
            FROM issue_comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.issue_id = :issue_id
            ORDER BY c.created_at ASC";

    $stmt = $pdo->prepare($sql);
    $stmt->execute([':issue_id' => $issueId]);
    $comments = $stmt->fetchAll(PDO::FETCH_ASSOC);

    sendJson(['success' => true, 'comments' => $comments]);
}

// 3.5. 新增留言 (POST /issue.php?action=issue/comment/create)
function handleCreateComment(PDO $pdo): void
{
    $issueId = $_POST['issue_id'] ?? null;
    $content = $_POST['content'] ?? null;
    $userId = getCurrentUserId();

    if ($userId === 0) {
        sendJson(['success' => false, 'message' => '請先登入，無法發送留言'], 401);
    }
    if (!$issueId || !$content) {
        sendJson(['success' => false, 'message' => '缺少必要參數'], 400);
    }

    try {
        $sql = "INSERT INTO issue_comments (issue_id, user_id, content) 
                VALUES (:issue_id, :user_id, :content) 
                RETURNING id, created_at";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            ':issue_id' => $issueId,
            ':user_id' => $userId,
            ':content' => $content
        ]);

        $newComment = $stmt->fetch(PDO::FETCH_ASSOC);

        // 獲取 username 以便前端立即顯示
        $userSql = "SELECT username FROM users WHERE id = :user_id";
        $userStmt = $pdo->prepare($userSql);
        $userStmt->execute([':user_id' => $userId]);
        $userData = $userStmt->fetch(PDO::FETCH_ASSOC);

        sendJson([
            'success' => true,
            'message' => '留言發送成功',
            'new_comment' => array_merge($newComment, [
                'user_id' => (int) $userId,
                'username' => $userData['username'] ?? '未知用戶',
                'content' => $content
            ])
        ]);

    } catch (PDOException $e) {
        sendJson(['success' => false, 'message' => '留言發送失敗：' . $e->getMessage()], 500);
    }
}


// ====================================================================
// 4. API 路由與處理 (Router)
//    - 呼叫點在此，確保在所有函式定義之後。
// ====================================================================

$requestAction = $_GET['action'] ?? null;
$requestMethod = $_SERVER['REQUEST_METHOD'];

if ($requestAction === 'issues/list' && $requestMethod === 'GET') {
    handleFetchIssues($pdo);

} elseif ($requestAction === 'issues/create' && $requestMethod === 'POST') {
    handleCreateIssue($pdo);

} elseif ($requestAction === 'issues/resolve' && $requestMethod === 'POST') {
    handleResolveIssue($pdo);

} elseif ($requestAction === 'issues/comments' && $requestMethod === 'GET') {
    handleFetchComments($pdo);

} elseif ($requestAction === 'issue/comment/create' && $requestMethod === 'POST') {
    handleCreateComment($pdo);

} else {
    // 預設錯誤處理
    sendJson(['success' => false, 'message' => '無效的 API 動作或方法'], 404);
}