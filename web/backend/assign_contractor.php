<?php
header('Content-Type: application/json; charset=utf-8');

$taskId = $_POST['task_id'] ?? null;
$contractorUsername = $_POST['contractor'] ?? null; // username 方案
$contractorIdInput = $_POST['contractor_id'] ?? null; // 若前端也改成送 id，可接受

if (!$taskId || (!$contractorUsername && !$contractorIdInput)) {
    echo json_encode(['success' => false, 'message' => '缺少參數']);
    exit;
}

try {
    $pdo = new PDO("pgsql:host=localhost;port=5432;dbname=project", "postgres", "0", [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);

    // 權限檢查（建議）：確認目前登入者為該任務的 poster（可選）
    session_start();
    $currentUser = $_SESSION['user_id'] ?? null;
    if ($currentUser) {
        $check = $pdo->prepare("SELECT poster_id FROM projects WHERE id = :task_id");
        $check->execute(['task_id' => $taskId]);
        $proj = $check->fetch(PDO::FETCH_ASSOC);
        if (!$proj) {
            echo json_encode(['success' => false, 'message' => '任務不存在']);
            exit;
        }
        // 若你要強制只有案主可以指派，取消下面註解
        // if (strval($proj['poster_id']) !== strval($currentUser)) {
        //     echo json_encode(['success' => false, 'message' => '沒有權限']);
        //     exit;
        // }
    }

    // 優先使用傳入的 contractor_id（若有）
    $contractorId = null;
    if ($contractorIdInput !== null && $contractorIdInput !== '') {
        $contractorId = intval($contractorIdInput);
    } else {
        // 以 username 查 users 表取 id
        $q = $pdo->prepare("SELECT id FROM users WHERE username = :uname LIMIT 1");
        $q->execute(['uname' => $contractorUsername]);
        $r = $q->fetch(PDO::FETCH_ASSOC);
        if (!$r) {
            echo json_encode(['success' => false, 'message' => '找不到對應使用者']);
            exit;
        }
        $contractorId = (int)$r['id'];
    }

    // 最終更新 projects.contractor_id（假設欄位為 integer）
    $upd = $pdo->prepare("UPDATE projects SET contractor_id = :contractor_id WHERE id = :task_id");
    $upd->execute(['contractor_id' => $contractorId, 'task_id' => $taskId]);

    echo json_encode(['success' => true]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => $e->getMessage()]);
}