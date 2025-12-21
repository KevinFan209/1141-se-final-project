<?php
session_start();
header('Content-Type: application/json; charset=utf-8');

if (!isset($_SESSION['user_id']) || !isset($_SESSION['username'])) {
    echo json_encode(['success' => false, 'message' => '尚未登入']);
    exit;
}

$userId = $_SESSION['user_id'];
$username = $_SESSION['username'];
$taskId = $_POST['task_id'] ?? null;

if (!$taskId) {
    echo json_encode(['success' => false, 'message' => '缺少任務 ID']);
    exit;
}

try {
    $pdo = new PDO("pgsql:host=localhost;port=5432;dbname=project", "postgres", "0", [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);

    // 檢查是否已提出意願（使用正確欄位 task_id）
    $check = $pdo->prepare("SELECT id FROM intents WHERE user_id = :uid AND task_id = :task_id");
    $check->execute(['uid' => $userId, 'task_id' => $taskId]);
    $existing = $check->fetch(PDO::FETCH_ASSOC);

    if ($existing) {
        // 已提出 → 刪除意願
        $del = $pdo->prepare("DELETE FROM intents WHERE id = :id");
        $del->execute(['id' => $existing['id']]);
        echo json_encode(['success' =>  true, 'action' => 'removed']);
    } else {
        // 尚未提出 → 新增意願
        $stmt = $pdo->prepare("
            INSERT INTO intents (user_id, username, task_id, message, attachments)
            VALUES (:uid, :uname, :task_id, '', '[]'::jsonb)
        ");
        $stmt->execute([
            'uid' => $userId,
            'uname' => $username,
            'task_id' => $taskId
        ]);
        echo json_encode(['success' => true, 'action' => 'added']);
    }
} catch (Exception $e) {
    echo json_encode(['success' => false, 'message' => $e->getMessage()]);
}