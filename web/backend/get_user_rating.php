<?php
header('Content-Type: application/json; charset=utf-8');

$dbHost = 'localhost'; $dbPort = '5432'; $dbName = 'project'; $dbUser = 'postgres'; $dbPass = '0';

$reviewee_id = $_GET['user_id'] ?? null;

if (!$reviewee_id) {
    echo json_encode(['success' => false, 'message' => '缺少 ID']);
    exit;
}

try {
    $dsn = "pgsql:host={$dbHost};port={$dbPort};dbname={$dbName}";
    $pdo = new PDO($dsn, $dbUser, $dbPass, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);

    // --- 關鍵修正：移除 role_type 的嚴格限制，確保能抓到資料 ---
    // 有些紀錄存 employer，有些存 freelancer，我們先通通抓出來
    $sqlStats = "SELECT 
                    COUNT(*) as total_count,
                    AVG(CAST((score_1 + score_2 + score_3) AS FLOAT) / 3.0) as avg_score
                 FROM reviews 
                 WHERE reviewee_id = :uid";
    
    $stmtStats = $pdo->prepare($sqlStats);
    $stmtStats->execute([':uid' => (int)$reviewee_id]);
    $stats = $stmtStats->fetch(PDO::FETCH_ASSOC);

    $sqlComments = "SELECT comment FROM reviews 
                    WHERE reviewee_id = :uid AND comment IS NOT NULL AND comment != ''
                    ORDER BY created_at DESC LIMIT 5";
    
    $stmtComments = $pdo->prepare($sqlComments);
    $stmtComments->execute([':uid' => (int)$reviewee_id]);
    $comments = $stmtComments->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode([
        'success' => true,
        'average_score' => $stats['avg_score'] ? round((float)$stats['avg_score'], 1) : 0,
        'total_reviews' => (int)$stats['total_count'],
        'reviews' => $comments
    ]);

} catch (Exception $e) {
    echo json_encode(['success' => false, 'message' => $e->getMessage()]);
}