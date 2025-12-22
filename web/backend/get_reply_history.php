<?php
// backend/get_reply_history.php
header('Content-Type: application/json; charset=utf-8');

// ====== 直接寫入資料庫連線資訊 ======
$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

try {
    // 建立 PDO 連線
    $dsn = "pgsql:host=$dbHost;port=$dbPort;dbname=$dbName";
    $pdo = new PDO($dsn, $dbUser, $dbPass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);

    // ====== 取得前端傳來的 Task ID ======
    $taskId = isset($_GET['task_id']) ? (int)$_GET['task_id'] : null;

    if (!$taskId) {
        echo json_encode(['success' => false, 'message' => '缺少案件 ID (Task ID)']);
        exit;
    }

    // ====== 查詢歷史紀錄 ======
    // 依照版本序號 (version_num) 由新到舊排序
    $stmt = $pdo->prepare("SELECT * FROM replie_history WHERE task_id = ? ORDER BY version_num DESC");
    $stmt->execute([$taskId]);
    $history = $stmt->fetchAll();

    // 回傳結果
    echo json_encode([
        'success' => true, 
        'history' => $history
    ], JSON_UNESCAPED_UNICODE);

} catch (PDOException $e) {
    // 處理連線或 SQL 錯誤
    http_response_code(500);
    echo json_encode([
        'success' => false, 
        'message' => '資料庫錯誤：' . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
} catch (Exception $e) {
    // 處理其他一般錯誤
    http_response_code(500);
    echo json_encode([
        'success' => false, 
        'message' => '系統錯誤：' . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}
?>