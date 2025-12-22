<?php
// backend/reject_reply.php
session_start();
header('Content-Type: application/json; charset=utf-8');

$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success'=>false,'message'=>'Method not allowed']);
    exit;
}

if (empty($_SESSION['user_id'])) {
    http_response_code(401);
    echo json_encode(['success'=>false,'message'=>'未登入']);
    exit;
}
$poster_id = intval($_SESSION['user_id']);

$reply_id = isset($_POST['reply_id']) ? intval($_POST['reply_id']) : null;
if (!$reply_id) {
    http_response_code(400);
    echo json_encode(['success'=>false,'message'=>'missing reply_id']);
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
    // optional: 檢查該 reply 是否屬於某 task，且該 task 屬於此 poster（避免權限問題）
    $stmt = $pdo->prepare("SELECT r.id, r.task_id, p.poster_id FROM replies r LEFT JOIN projects p ON p.id = r.task_id WHERE r.id = :reply_id");
    $stmt->execute([':reply_id'=>$reply_id]);
    $row = $stmt->fetch();
    if (!$row) {
        http_response_code(404);
        echo json_encode(['success'=>false,'message'=>'reply not found']);
        exit;
    }
    if (intval($row['poster_id']) !== $poster_id) {
        http_response_code(403);
        echo json_encode(['success'=>false,'message'=>'沒有權限退件']);
        exit;
    }

    $stmt = $pdo->prepare("UPDATE replies SET status = 'rejected' WHERE id = :reply_id");
    $stmt->execute([':reply_id'=>$reply_id]);

    echo json_encode(['success'=>true]);
    exit;
} catch (PDOException $e) {
    error_log("reject_reply error: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success'=>false,'message'=>'DB error']);
    exit;
}