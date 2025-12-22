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

define('UPLOAD_DIR', __DIR__ . '/uploads');

function json_resp($arr, $code = 200) {
    http_response_code($code);
    echo json_encode($arr, JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    json_resp(['success' => false, 'message' => 'Method not allowed'], 405);
}

if (empty($_SESSION['user_id'])) {
    json_resp(['success' => false, 'message' => '未登入或 session 過期'], 401);
}
$responder_id = (int)$_SESSION['user_id'];

$task_id = isset($_POST['task_id']) ? (int)$_POST['task_id'] : 0;
// 前端傳來的欄位名稱可能是 price_text 或 price，請與 HTML 對應
$price   = isset($_POST['price_text']) ? trim($_POST['price_text']) : (isset($_POST['price']) ? trim($_POST['price']) : '');
$message = isset($_POST['message']) ? trim($_POST['message']) : null;

if ($task_id <= 0 || $price === '') {
    json_resp(['success' => false, 'message' => '缺少必要欄位'], 400);
}

// ====== 處理檔案上傳 (保持唯一檔名，不覆蓋) ======
$attachments = [];
if (!empty($_FILES['reply_files']) && is_array($_FILES['reply_files']['name'])) {
    if (!is_dir(UPLOAD_DIR)) mkdir(UPLOAD_DIR, 0755, true);

    foreach ($_FILES['reply_files']['name'] as $i => $name) {
        if ($_FILES['reply_files']['error'][$i] !== UPLOAD_ERR_OK) continue;

        $tmp  = $_FILES['reply_files']['tmp_name'][$i];
        $size = $_FILES['reply_files']['size'][$i];
        $type = mime_content_type($tmp);

        if ($size <= 0 || $size > 15 * 1024 * 1024) continue;
        
        $ext = pathinfo($name, PATHINFO_EXTENSION);
        // 使用隨機名稱確保伺服器上的檔案永不覆蓋
        $safeName = bin2hex(random_bytes(8)) . '_' . time() . '.' . $ext;
        $dest = UPLOAD_DIR . '/' . $safeName;

        if (move_uploaded_file($tmp, $dest)) {
            $attachments[] = [
                'filename' => $safeName,
                'orig_name' => $name,
                'mime' => $type,
                'path' => 'backend/uploads/' . $safeName
            ];
        }
    }
}
$attachments_json = json_encode($attachments, JSON_UNESCAPED_UNICODE);

// ====== 資料庫操作 ======
$dsn = "pgsql:host=$dbHost;port=$dbPort;dbname=$dbName";
try {
    $pdo = new PDO($dsn, $dbUser, $dbPass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);

    $pdo->beginTransaction(); // 開始交易

    // 1️⃣ 取得該任務當前最大版本號
    $vSql = "SELECT COALESCE(MAX(version_num), 0) FROM replie_history WHERE task_id = :tid";
    $vStmt = $pdo->prepare($vSql);
    $vStmt->execute([':tid' => $task_id]);
    $nextVersion = $vStmt->fetchColumn() + 1;

    // 2️⃣ 寫入歷史紀錄表 (replie_history)
    $historySql = "
        INSERT INTO replie_history 
        (task_id, user_id, price, content, attachments, version_num, created_at)
        VALUES 
        (:tid, :uid, :price, :content, :attachments::jsonb, :vnum, now())
        RETURNING id
    ";
    $hStmt = $pdo->prepare($historySql);
    $hStmt->execute([
        ':tid'         => $task_id,
        ':uid'         => $responder_id,
        ':price'       => $price,
        ':content'     => $message,
        ':attachments' => $attachments_json,
        ':vnum'        => $nextVersion
    ]);
    $history_id = $hStmt->fetchColumn();

    // 3️⃣ 更新任務主表的狀態 (標記為已回覆，讓業主知道有新進度)
    // 假設任務表為 tasks，欄位為 status
    $updateTaskSql = "UPDATE projects SET status = 'review', updated_at = now() WHERE id = :tid";

$pdo->prepare($updateTaskSql)->execute([':tid' => $task_id]);

    $pdo->commit(); // 提交交易

    json_resp([
        'success' => true,
        'message' => '回覆已成功送出',
        'version' => $nextVersion,
        'history_id' => $history_id
    ]);

} catch (Exception $e) {
    if ($pdo->inTransaction()) $pdo->rollBack();
    error_log($e->getMessage());
    json_resp(['success' => false, 'message' => '儲存失敗：' . $e->getMessage()], 500);
}