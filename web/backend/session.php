<?php
// 啟用安全的 session 設定
session_set_cookie_params([
    'lifetime' => 0,
    'path' => '/',
    'domain' => '',        // 如需跨子域請設定
    'secure' => isset($_SERVER['HTTPS']), // HTTPS 時才傳送
    'httponly' => true,
    'samesite' => 'Lax'
]);
session_start();

// 簡單的 JSON 回應函式
function json_resp(array $data, int $status = 200) {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

// 檢查 session 中的 user 資訊
if (!isset($_SESSION['user']) || empty($_SESSION['user'])) {
    json_resp(['success' => false, 'message' => '未登入或 session 遺失'], 401);
}

// 假設登入時把使用者資料放在 $_SESSION['user']
$user = $_SESSION['user'];

// 回傳使用者資訊（移除敏感欄位）
unset($user['password']);
json_resp(['success' => true, 'user' => $user]);