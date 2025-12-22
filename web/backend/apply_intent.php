<?php
session_start();
header('Content-Type: application/json; charset=utf-8');

// 1. 檢查登入與參數
if (!isset($_SESSION['user_id'])) {
    echo json_encode(['success' => false, 'message' => '尚未登入']);
    exit;
}

$userId = $_SESSION['user_id'];
$username = $_SESSION['username'] ?? 'Unknown';
$taskId = $_POST['task_id'] ?? null;

if (!$taskId) {
    echo json_encode(['success' => false, 'message' => '缺少任務 ID']);
    exit;
}

// 2. 檢查檔案上傳 (無論新增或更新都需要檔案)
if (!isset($_FILES['proposal_pdf']) || $_FILES['proposal_pdf']['error'] !== UPLOAD_ERR_OK) {
    echo json_encode(['success' => false, 'message' => '請上傳 PDF 計畫書']);
    exit;
}

try {
    $pdo = new PDO("pgsql:host=localhost;port=5432;dbname=project", "postgres", "0", [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);

    // 處理檔案儲存
    $file = $_FILES['proposal_pdf'];
    $uploadDir = "D:/工作/phpweb/www/web/uploads/proposals/";
    if (!is_dir($uploadDir)) mkdir($uploadDir, 0777, true);

    $newFileName = "T{$taskId}_U{$userId}_" . date("YmdHis") . ".pdf";
    $destPath = $uploadDir . $newFileName;

    if (!move_uploaded_file($file['tmp_name'], $destPath)) {
        throw new Exception("檔案儲存失敗");
    }

    $attachmentsJson = json_encode([[
        'orig_name' => $file['name'],
        'file_name' => $newFileName,
        'url' => 'uploads/proposals/' . $newFileName,
        'mime' => 'application/pdf'
    ]]);

    // 3. 檢查是否存在舊紀錄
    $check = $pdo->prepare("SELECT id FROM intents WHERE user_id = :uid AND task_id = :tid");
    $check->execute(['uid' => $userId, 'tid' => $taskId]);
    $existing = $check->fetch();

    if ($existing) {
        // 執行更新 (UPDATE)
        $sql = "UPDATE intents SET attachments = :attach::jsonb, message = :msg WHERE id = :id";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            'id'     => $existing['id'],
            'attach' => $attachmentsJson,
            'msg'    => 'Proposal Updated at ' . date("Y-m-d H:i:s")
        ]);
        echo json_encode(['success' => true, 'action' => 'updated']);
    } else {
        // 執行新增 (INSERT)
        $sql = "INSERT INTO intents (user_id, username, task_id, message, attachments) 
                VALUES (:uid, :uname, :tid, :msg, :attach::jsonb)";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            'uid'    => $userId,
            'uname'  => $username,
            'tid'    => $taskId,
            'msg'    => 'First Proposal Uploaded',
            'attach' => $attachmentsJson
        ]);
        echo json_encode(['success' => true, 'action' => 'added']);
    }

} catch (Exception $e) {
    echo json_encode(['success' => false, 'message' => $e->getMessage()]);
}