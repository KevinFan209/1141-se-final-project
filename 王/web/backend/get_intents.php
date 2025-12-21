<?php
header('Content-Type: application/json; charset=utf-8');

$taskId = $_GET['task_id'] ?? null;
if (!$taskId) {
    echo json_encode([]);
    exit;
}

try {
    $pdo = new PDO("pgsql:host=localhost;port=5432;dbname=project", "postgres", "0", [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);

    // 回傳 user_id 與 username，方便前端以 id 做後續操作
    $stmt = $pdo->prepare("SELECT user_id, username, quote, message, created_at FROM intents WHERE task_id = :task_id ORDER BY created_at ASC");
    $stmt->execute(['task_id' => $taskId]);
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode($rows);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([]);
}