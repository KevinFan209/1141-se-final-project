<?php
// backend/delete_task.php
header('Content-Type: application/json; charset=utf-8');

$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => 'Method not allowed']);
    exit;
}

$id = intval($_POST['id'] ?? 0);
if ($id <= 0) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Invalid ID']);
    exit;
}

try {
    $pdo = new PDO("pgsql:host=$dbHost;port=$dbPort;dbname=$dbName", $dbUser, $dbPass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);

    // 使用交易，確保 intents 與 projects 一起刪除
    $pdo->beginTransaction();
    // 先刪除 intents 中相關的紀錄
    $stmtIntents = $pdo->prepare("DELETE FROM intents WHERE task_id = :id");
    $stmtIntents->execute([':id' => $id]);

    // 再刪除 projects
    $stmt = $pdo->prepare("DELETE FROM projects WHERE id = :id");
    $stmt->execute([':id' => $id]);

    $pdo->commit();

    echo json_encode(['success' => true]);
} catch (PDOException $e) {
    if (isset($pdo) && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Delete failed', 'error' => $e->getMessage()]);
}
