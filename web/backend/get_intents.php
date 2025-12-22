<?php
header('Content-Type: application/json; charset=utf-8');

$taskId = isset($_GET['task_id']) ? (int)$_GET['task_id'] : null;

if (!$taskId) {
    echo json_encode([]);
    exit;
}

try {
    $pdo = new PDO("pgsql:host=localhost;port=5432;dbname=project", "postgres", "0", [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
    ]);

    // 【修正重點】加入 attachments 欄位，這才能讓前端抓到檔案
    $sql = "SELECT 
                user_id, 
                username, 
                quote, 
                message, 
                attachments, 
                created_at 
            FROM intents 
            WHERE task_id = :task_id 
            ORDER BY created_at ASC";

    $stmt = $pdo->prepare($sql);
    $stmt->execute(['task_id' => $taskId]);
    $rows = $stmt->fetchAll();

    // 回傳資料
    echo json_encode($rows, JSON_UNESCAPED_UNICODE);

} catch (Exception $e) {
    http_response_code(500);
    // 輸出錯誤訊息方便 Debug，正式上線後可改回空陣列
    echo json_encode([
        "error" => "Database error: " . $e->getMessage()
    ]);
}