<?php
session_start();
header('Content-Type: application/json; charset=utf-8');

// 資料庫連線設定
$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

try {
    $pdo = new PDO("pgsql:host=$dbHost;port=$dbPort;dbname=$dbName", $dbUser, $dbPass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);
} catch (PDOException $e) {
    echo json_encode(['success' => false, 'message' => '資料庫連線失敗']);
    exit;
}

// 取得 JSON 資料
$input = json_decode(file_get_contents('php://input'), true);
$username = trim($input['username'] ?? '');
$password = $input['password'] ?? '';

if (!$username || !$password) {
    echo json_encode(['success' => false, 'message' => '請輸入帳號與密碼']);
    exit;
}

// 查詢使用者是否存在
$stmt = $pdo->prepare("SELECT * FROM users WHERE username = :username");
$stmt->execute(['username' => $username]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if ($user) {
    // 驗證密碼
    if ($user && password_verify($password, $user['password_hash'])) {
        $_SESSION['user_id'] = $user['id'];           // ✅ 儲存使用者 ID
        $_SESSION['username'] = $user['username'];    // ✅ 儲存使用者名稱
        echo json_encode(['success' => true, 'message' => '登入成功']);
    } else {
        echo json_encode(['success' => false, 'message' => '密碼錯誤']);
    }
}  else {
    // 自動註冊
    $hash = password_hash($password, PASSWORD_DEFAULT); // ✅ 補上這行

    $insert = $pdo->prepare("INSERT INTO users (username, password_hash) VALUES (:username, :hash)");
    $insert->execute(['username' => $username, 'hash' => $hash]);

    // 取得新使用者 ID
    $newId = $pdo->lastInsertId();

    $_SESSION['user_id'] = $newId;                   // ✅ 儲存新使用者 ID
    $_SESSION['username'] = $username;
    echo json_encode(['success' => true, 'message' => '註冊成功，已登入']);
}