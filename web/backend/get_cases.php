<?php
// backend/get_cases.php
header('Content-Type: application/json; charset=utf-8');

$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

try {
    $dsn = "pgsql:host={$dbHost};port={$dbPort};dbname={$dbName}";
    $pdo = new PDO($dsn, $dbUser, $dbPass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Database connection failed']);
    exit;
}

try {
    // 包含 contractor_id（若欄位名稱不同請改為你實際的欄位名）
    $stmt = $pdo->query("SELECT id, title, description, budget, region, attachments, created_at, closed_at, poster_id, is_completed, contractor_id FROM projects ORDER BY created_at DESC");
    $rows = $stmt->fetchAll();

    foreach ($rows as &$row) {
        $row['avatar'] = '👤';
        $row['username'] = $row['title'];
        $row['phone'] = '';
        $row['published_at'] = $row['created_at'];
    }

    echo json_encode($rows, JSON_UNESCAPED_UNICODE);
    exit;
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Query failed']);
    exit;
}