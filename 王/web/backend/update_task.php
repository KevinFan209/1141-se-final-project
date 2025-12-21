<?php
header('Content-Type: application/json; charset=utf-8');

$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

$id = intval($_POST['id'] ?? 0);
$title = $_POST['title'] ?? '';
$budget = $_POST['budget'] ?? '';
$region = $_POST['region'] ?? '';
$description = $_POST['description'] ?? '';
$closed_at = $_POST['closed_at'] ?? null;
if ($closed_at === '' || $closed_at === 'null') {
  $closed_at = null;
}
// 處理檔案上傳
$attachments = [];

if (!empty($_FILES['taskFiles']) && is_array($_FILES['taskFiles']['name'])) {
  foreach ($_FILES['taskFiles']['tmp_name'] as $i => $tmpPath) {
    if (!is_uploaded_file($tmpPath)) continue;

    $origName = $_FILES['taskFiles']['name'][$i];
    $mime = $_FILES['taskFiles']['type'][$i];
    $targetPath = 'uploads/' . uniqid() . '_' . basename($origName);

    if (move_uploaded_file($tmpPath, $targetPath)) {
      $attachments[] = [
        'filename' => $origName,
        'path' => $targetPath,
        'mime' => $mime
      ];
    }
  }
}

$attachmentsJson = count($attachments) > 0 ? json_encode($attachments) : ($_POST['attachments'] ?? null);

// ✅ 加在這裡：若沒上傳新檔案，保留原本的 attachments
if (count($attachments) === 0 && isset($_POST['attachments'])) {
  $attachmentsJson = $_POST['attachments'];
} else {
  $attachmentsJson = json_encode($attachments);
}

$attachmentsJson = count($attachments) > 0 ? json_encode($attachments) : null;

if ($id <= 0 || !$title || !$region) {
  http_response_code(400);
  echo json_encode(['success' => false, 'message' => '缺少必要欄位']);
  exit;
}

try {
  $pdo = new PDO("pgsql:host=$dbHost;port=$dbPort;dbname=$dbName", $dbUser, $dbPass, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
  ]);

  $stmt = $pdo->prepare("UPDATE projects SET title = :title, budget = :budget, region = :region, description = :description, closed_at = :closed_at, attachments = :attachments WHERE id = :id");

$stmt->execute([
  ':title' => $title,
  ':budget' => $budget,
  ':region' => $region,
  ':description' => $description,
  ':closed_at' => $closed_at,
  ':attachments' => $attachmentsJson,
  ':id' => $id
]);

  echo json_encode(['success' => true]);
} catch (PDOException $e) {
  http_response_code(500);
  echo json_encode(['success' => false, 'message' => '更新失敗', 'error' => $e->getMessage()]);
}