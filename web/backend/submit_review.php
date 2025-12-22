<?php
header('Content-Type: application/json; charset=utf-8');
session_start();

// 資料庫連線資訊
$host = "localhost";
$port = "5432";
$dbname = "project";
$user = "postgres";
$password = "0";

try {
    $pdo = new PDO("pgsql:host=$host;port=$port;dbname=$dbname", $user, $password, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);

    // 1. 取得 POST 資料
    $taskId    = $_POST['task_id'] ?? null;
    $roleType  = $_POST['role_type'] ?? null; // 'client' 或 'freelancer'
    $score1    = intval($_POST['score_1'] ?? 0);
    $score2    = intval($_POST['score_2'] ?? 0);
    $score3    = intval($_POST['score_3'] ?? 0);
    $comment   = trim($_POST['comment'] ?? '');
    
    // 從 Session 取得當前登入者 ID
    $reviewerId = $_SESSION['user_id'] ?? null; 

    if (!$reviewerId) {
        throw new Exception("請先登入後再進行評價");
    }

    if (!$taskId || !$roleType) {
        throw new Exception("缺少必要參數");
    }

    // 2. 從 projects 表中查詢對應的發案人與接案人
    // 【修正點】表名改為 projects，欄位改為 poster_id 與 contractor_id
    $stmtTask = $pdo->prepare("SELECT poster_id, contractor_id FROM projects WHERE id = ?");
    $stmtTask->execute([$taskId]);
    $project = $stmtTask->fetch(PDO::FETCH_ASSOC);

    if (!$project) {
        throw new Exception("找不到該案件紀錄");
    }

    // 3. 確定誰是被評價的人 (Reviewee)
    if ($roleType === 'client') {
        // 甲方(poster)評乙方(contractor)
        $revieweeId = $project['contractor_id'];
    } else {
        // 乙方(contractor)評甲方(poster)
        $revieweeId = $project['poster_id'];
    }

    if (!$revieweeId) {
        throw new Exception("該案件尚未指派接案人或找不到受評對象");
    }

    // 4. 檢查是否重複評價
    $stmtCheck = $pdo->prepare("SELECT id FROM reviews WHERE task_id = ? AND reviewer_id = ?");
    $stmtCheck->execute([$taskId, $reviewerId]);
    if ($stmtCheck->fetch()) {
        throw new Exception("您已經評價過此案件");
    }

    // 5. 寫入 reviews 表
    $sql = "INSERT INTO reviews (task_id, reviewer_id, reviewee_id, role_type, score_1, score_2, score_3, comment) 
            VALUES (:tid, :rid, :eeid, :role, :s1, :s2, :s3, :msg)";
    
    $stmt = $pdo->prepare($sql);
    $stmt->execute([
        ':tid'  => $taskId,
        ':rid'  => $reviewerId,
        ':eeid' => $revieweeId,
        ':role' => $roleType,
        ':s1'   => $score1,
        ':s2'   => $score2,
        ':s3'   => $score3,
        ':msg'  => $comment
    ]);

    echo json_encode(['success' => true, 'message' => '評價提交成功']);

} catch (Exception $e) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => $e->getMessage()]);
}