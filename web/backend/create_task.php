<?php
// backend/create_task.php
session_start();
header('Content-Type: application/json; charset=utf-8');

// ---------- config ----------
$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

// Windows absolute path to your uploads folder
define('UPLOAD_DIR', 'D:\\工作\\phpweb\\www\\web\\backend\\uploads');
// URL prefix that maps to the above folder from the browser
define('WEB_UPLOAD_PREFIX', '/web/backend/uploads');
// ---------- end config ----------

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => 'Method not allowed']);
    exit;
}

// ----- 取 poster_id：優先使用 session，其次接受 POST 備援 -----
// 在 create_task.php 開頭（session_start() 之後）放入：
$poster_id = null;
// 印出 session 與 POST 供排錯（上線後可移除）
error_log("create_task.php: \$_COOKIE = " . json_encode($_COOKIE));
error_log("create_task.php: \$_SESSION before = " . json_encode($_SESSION));
error_log("create_task.php: \$_POST keys = " . json_encode(array_keys($_POST)));

// 優先使用 session 裡的 user id
if (!empty($_SESSION['user_id'])) {
    $poster_id = (int) $_SESSION['user_id'];
    error_log("create_task.php: poster_id from session = " . $poster_id);
} elseif (isset($_POST['poster_id']) && $_POST['poster_id'] !== '') {
    $poster_id = (int) $_POST['poster_id'];
    error_log("create_task.php: poster_id from POST = " . $poster_id);
} else {
    error_log("create_task.php: poster_id not found in session or POST");
}

// Basic validation
$title = trim($_POST['title'] ?? '');
$description = trim($_POST['description'] ?? '');
$budget = trim($_POST['budget'] ?? '');
$region = trim($_POST['region'] ?? '');
$closed_at = isset($_POST['closed_at']) && $_POST['closed_at'] !== '' && $_POST['closed_at'] !== 'null'
    ? $_POST['closed_at']
    : null;

if ($title === '') {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'title is required']);
    exit;
}

// Ensure upload dir exists
if (!is_dir(UPLOAD_DIR)) {
    if (!mkdir(UPLOAD_DIR, 0755, true)) {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Failed to create upload dir']);
        exit;
    }
}

// Handle uploaded files (expecting input name "taskFiles[]" from your form)
$attachments = [];
if (!empty($_FILES['taskFiles'])) {
    $files = $_FILES['taskFiles'];
    for ($i = 0; $i < count($files['name']); $i++) {
        if ($files['error'][$i] !== UPLOAD_ERR_OK) continue;

        $origName = basename($files['name'][$i]);
        $tmpName = $files['tmp_name'][$i];
        $mime = mime_content_type($tmpName) ?: $files['type'][$i];

        $ext = pathinfo($origName, PATHINFO_EXTENSION);
        $extClean = $ext ? '.' . preg_replace('/[^a-zA-Z0-9]/', '', $ext) : '';
        try {
            $safeBase = bin2hex(random_bytes(8));
        } catch (Exception $e) {
            $safeBase = substr(md5(uniqid('', true)), 0, 16);
        }
        $safeName = $safeBase . $extClean;
        $targetPath = rtrim(UPLOAD_DIR, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . $safeName;

        if (!move_uploaded_file($tmpName, $targetPath)) {
            error_log("create_task.php: move_uploaded_file failed for {$origName} -> {$targetPath}");
            continue;
        }

        $url = rtrim(WEB_UPLOAD_PREFIX, '/') . '/' . $safeName;

        $attachments[] = [
            'orig_name' => $origName,
            'file_name' => $safeName,
            'mime' => $mime,
            'url' => $url
        ];
    }
}

// Connect to DB
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
    $pdo->beginTransaction();

    $sql = "INSERT INTO projects (title, description, budget, region, attachments, closed_at, poster_id)
            VALUES (:title, :description, :budget, :region, :attachments::jsonb, :closed_at, :poster_id)
            RETURNING id, created_at";

    $stmt = $pdo->prepare($sql);
    $stmt->bindValue(':title', $title);
    $stmt->bindValue(':description', $description);
    $stmt->bindValue(':budget', $budget);
    $stmt->bindValue(':region', $region);
    $stmt->bindValue(':attachments', json_encode($attachments, JSON_UNESCAPED_UNICODE));

    if ($closed_at === null) {
        $stmt->bindValue(':closed_at', null, PDO::PARAM_NULL);
    } else {
        $stmt->bindValue(':closed_at', $closed_at, PDO::PARAM_STR);
    }

    // 這裡正確綁定 poster_id（可能為 NULL）
    if ($poster_id === null) {
        $stmt->bindValue(':poster_id', null, PDO::PARAM_NULL);
    } else {
        $stmt->bindValue(':poster_id', $poster_id, PDO::PARAM_INT);
    }

    $stmt->execute();

    $inserted = $stmt->fetch();
    $pdo->commit();

    echo json_encode([
        'success' => true,
        'id' => $inserted['id'] ?? null,
        'created_at' => $inserted['created_at'] ?? null,
        'attachments' => $attachments
    ]);
    exit;
} catch (PDOException $e) {
    if ($pdo->inTransaction()) $pdo->rollBack();
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Insert failed',
        'error' => $e->getMessage()
    ]);
    exit;
}