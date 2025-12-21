<?php
// backend/accept_reply.php
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
$task_id = isset($_POST['task_id']) ? intval($_POST['task_id']) : null;
if (!$reply_id || !$task_id) {
    http_response_code(400);
    echo json_encode(['success'=>false,'message'=>'missing reply_id or task_id']);
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
    // 確認 task 屬於目前 session 使用者（避免非刊登者操作）
    $stmt = $pdo->prepare("SELECT id, poster_id FROM projects WHERE id = :task_id");
    $stmt->execute([':task_id'=>$task_id]);
    $task = $stmt->fetch();
    if (!$task) {
        http_response_code(404);
        echo json_encode(['success'=>false,'message'=>'task not found']);
        exit;
    }
    if (intval($task['poster_id']) !== $poster_id) {
        http_response_code(403);
        echo json_encode(['success'=>false,'message'=>'沒有權限接受回復']);
        exit;
    }

    $pdo->beginTransaction();

    // 1) 把其他回復標成 rejected（optional），把這筆標成 accepted
    $stmt = $pdo->prepare("UPDATE replies SET status = 'rejected' WHERE task_id = :task_id AND id != :reply_id");
    $stmt->execute([':task_id'=>$task_id, ':reply_id'=>$reply_id]);

    $stmt = $pdo->prepare("UPDATE replies SET status = 'accepted' WHERE id = :reply_id RETURNING responder_id");
    $stmt->execute([':reply_id'=>$reply_id]);
    $res = $stmt->fetch();
    if (!$res) {
        $pdo->rollBack();
        http_response_code(404);
        echo json_encode(['success'=>false,'message'=>'reply not found']);
        exit;
    }
    $responder_id = intval($res['responder_id']);

    // 2) 將 projects.contractor_id 設為該 responder（若你的 projects 表有此欄）
    //    並可選擇把 is_completed 設為 true 或保留
    $stmt = $pdo->prepare("UPDATE projects SET contractor_id = :responder_id, is_completed = true WHERE id = :task_id");
    $stmt->execute([':responder_id'=>$responder_id, ':task_id'=>$task_id]);

    $pdo->commit();
    echo json_encode(['success'=>true]);
    exit;
} catch (PDOException $e) {
    if ($pdo->inTransaction()) $pdo->rollBack();
    error_log("accept_reply error: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success'=>false,'message'=>'DB error']);
    exit;
}