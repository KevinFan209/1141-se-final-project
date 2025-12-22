<?php
header('Content-Type: application/json; charset=utf-8');
session_start();

try {
    $pdo = new PDO("pgsql:host=localhost;port=5432;dbname=project", "postgres", "0", [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);

    // 直接讓 attachments 若為 NULL 則回傳空陣列 JSON
    $sql = "
      SELECT id, title, budget, region, description, closed_at, poster_id,
             COALESCE(attachments, '[]'::jsonb) AS attachments
      FROM projects
      WHERE is_completed IS NOT TRUE
      ORDER BY created_at DESC
    ";

    $stmt = $pdo->query($sql);
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $tasks = [];
    foreach ($rows as $r) {
        // attachments 會是 JSON 字串（PDO 回傳），嘗試 decode 為 PHP 陣列
        $att = [];
        if (!empty($r['attachments'])) {
            // attachments 有可能是 already JSON string; decode safely
            $decoded = json_decode($r['attachments'], true);
            if (json_last_error() === JSON_ERROR_NONE && is_array($decoded)) {
                $att = $decoded;
            } else {
                $att = []; // 若 decode 失敗，回傳空陣列以免前端掛掉
            }
        }
        $tasks[] = [
            'id' => $r['id'],
            'title' => $r['title'],
            'reward' => 'NT$' . $r['budget'],
            'deadline' => $r['closed_at'],
            'region' => $r['region'],
            'desc' => $r['description'],
            'poster_id' => $r['poster_id'],
            'attachments' => $att
        ];
    }

    echo json_encode($tasks, JSON_UNESCAPED_UNICODE);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => '資料庫錯誤', 'message' => $e->getMessage()]);
}