<?php
// backend/reply_owner.php
session_start();
header('Content-Type: application/json; charset=utf-8');

// ====== 基本設定 ======
$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

// 上傳資料夾（請確定存在 & Apache 有權限）
define('UPLOAD_DIR', __DIR__ . '/uploads');

// ====== 工具函式 ======
function json_resp($arr, $code = 200) {
    http_response_code($code);
    echo json_encode($arr, JSON_UNESCAPED_UNICODE);
    exit;
}

// ====== 只允許 POST ======
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    json_resp(['success' => false, 'message' => 'Method not allowed'], 405);
}

// ====== 檢查登入（session） ======
if (empty($_SESSION['user_id'])) {
    json_resp(['success' => false, 'message' => '未登入或 session 過期'], 401);
}
$responder_id = (int)$_SESSION['user_id'];

// ====== 取得表單資料 ======
$task_id = isset($_POST['task_id']) ? (int)$_POST['task_id'] : 0;
$price   = isset($_POST['price']) ? trim($_POST['price']) : '';
$message = isset($_POST['message']) ? trim($_POST['message']) : null;

if ($task_id <= 0 || $price === '') {
    json_resp(['success' => false, 'message' => '缺少必要欄位'], 400);
}

// ====== 處理檔案上傳 ======
$attachments = [];

if (!empty($_FILES['reply_files']) && is_array($_FILES['reply_files']['name'])) {
    if (!is_dir(UPLOAD_DIR)) {
        mkdir(UPLOAD_DIR, 0755, true);
    }

    foreach ($_FILES['reply_files']['name'] as $i => $name) {
        if ($_FILES['reply_files']['error'][$i] !== UPLOAD_ERR_OK) continue;

        $tmp  = $_FILES['reply_files']['tmp_name'][$i];
        $size = $_FILES['reply_files']['size'][$i];
        $type = mime_content_type($tmp);

        if ($size <= 0 || $size > 15 * 1024 * 1024) continue;
        if (!in_array($type, ['image/jpeg','image/png','image/gif','application/pdf'])) continue;

        $ext = pathinfo($name, PATHINFO_EXTENSION);
        $safeName = bin2hex(random_bytes(8)) . '.' . $ext;
        $dest = UPLOAD_DIR . '/' . $safeName;

        if (move_uploaded_file($tmp, $dest)) {
            $attachments[] = [
                'filename' => $safeName,
                'orig_name' => $name,
                'mime' => $type,
                'path' => 'uploads/' . $safeName
            ];
        }
    }
}

$attachments_json = json_encode($attachments, JSON_UNESCAPED_UNICODE);

// ====== 寫入 PostgreSQL ======
$dsn = "pgsql:host=$dbHost;port=$dbPort;dbname=$dbName";
try {
    $pdo = new PDO($dsn, $dbUser, $dbPass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);
} catch (PDOException $e) {
    json_resp(['success' => false, 'message' => '資料庫連線失敗'], 500);
}

try {
    // 1️⃣ 先嘗試更新
    $updateSql = "
        UPDATE replies
        SET
            price_text = :price,
            message = :message,
            attachments = :attachments::jsonb,
            updated_at = now(),
            status = 'pending'
        WHERE task_id = :task_id
          AND responder_id = :responder_id
        RETURNING id
    ";

    $stmt = $pdo->prepare($updateSql);
    $stmt->execute([
        ':price'        => $price,
        ':message'      => $message ?: null,
        ':attachments'  => $attachments_json,
        ':task_id'      => $task_id,
        ':responder_id' => $responder_id
    ]);

    $id = $stmt->fetchColumn();

    // 2️⃣ 如果沒有更新任何資料 → 代表第一次回覆 → INSERT
    if (!$id) {
        $insertSql = "
            INSERT INTO replies
            (task_id, responder_id, price_text, message, attachments, status, created_at, updated_at)
            VALUES
            (:task_id, :responder_id, :price, :message, :attachments::jsonb, 'pending', now(), now())
            RETURNING id
        ";

        $stmt = $pdo->prepare($insertSql);
        $stmt->execute([
            ':task_id'      => $task_id,
            ':responder_id' => $responder_id,
            ':price'        => $price,
            ':message'      => $message ?: null,
            ':attachments'  => $attachments_json
        ]);

        $id = $stmt->fetchColumn();
    }

    json_resp([
        'success' => true,
        'id' => $id,
        'mode' => $id ? 'updated_or_inserted' : 'unknown'
    ]);

} catch (PDOException $e) {
    error_log($e->getMessage());
    json_resp(['success' => false, 'message' => '資料寫入失敗'], 500);
}
