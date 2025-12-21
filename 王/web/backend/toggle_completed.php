<?php
header('Content-Type: application/json; charset=utf-8');

$dbHost = 'localhost';
$dbPort = '5432';
$dbName = 'project';
$dbUser = 'postgres';
$dbPass = '0';

$id = $_POST['id'] ?? '';
if (!preg_match('/^\d+$/', $id)) {
  echo json_encode(['success' => false, 'message' => 'ID 格式錯誤']);
  exit;
}

try {
  $pdo = new PDO("pgsql:host=$dbHost;port=$dbPort;dbname=$dbName", $dbUser, $dbPass, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
  ]);

  $stmt = $pdo->prepare("SELECT is_completed FROM projects WHERE id = ?");
  $stmt->execute([$id]);
  $row = $stmt->fetch();

  if (!$row || !array_key_exists('is_completed', $row)) {
    echo json_encode(['success' => false, 'message' => '找不到資料']);
    exit;
  }

  $current = $row['is_completed'];
  $currentBool = ($current === 't' || $current === true || $current === 1);
  $newStatus = !$currentBool;

  $stmt = $pdo->prepare("UPDATE projects SET is_completed = CAST(:status AS BOOLEAN) WHERE id = :id");
  $stmt->execute([
    ':status' => $newStatus ? 'true' : 'false',
    ':id' => $id
  ]);

  echo json_encode(['success' => true, 'newStatus' => $newStatus]);
} catch (PDOException $e) {
  http_response_code(500);
  echo json_encode(['success' => false, 'message' => '更新失敗', 'error' => $e->getMessage()]);
}