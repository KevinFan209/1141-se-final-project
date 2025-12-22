<?php
// backend/get_replies.php
session_start();
header('Content-Type: application/json; charset=utf-8');

$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

$task_id = isset($_GET['task_id']) ? intval($_GET['task_id']) : null;
if (!$task_id) {
    http_response_code(400);
    echo json_encode(['success'=>false,'message'=>'missing task_id']);
    exit;
}

try {
    $dsn = "pgsql:host={$dbHost};port={$dbPort};dbname={$dbName}";
    $pdo = new PDO($dsn, $dbUser, $dbPass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success'=>false,'message'=>'DB connect failed']);
    exit;
}

try {
    $sql = "SELECT r.id, r.task_id, r.responder_id, r.price_text, r.message, r.attachments, r.status, r.created_at,
                   u.username as responder_name
            FROM replies r
            LEFT JOIN users u ON u.id = r.responder_id
            WHERE r.task_id = :task_id
            ORDER BY r.created_at ASC";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([':task_id' => $task_id]);
    $rows = $stmt->fetchAll();

    echo json_encode($rows, JSON_UNESCAPED_UNICODE);
    exit;
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success'=>false,'message'=>'Query failed']);
    exit;
}