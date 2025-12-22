<?php
session_start();
header('Content-Type: application/json; charset=utf-8');

if (!isset($_SESSION['user_id'])) {
    echo json_encode(['hasIntent' => false]);
    exit;
}

$userId = $_SESSION['user_id'];
$taskId = $_GET['task_id'] ?? null;

if (!$taskId) {
    echo json_encode(['hasIntent' => false]);
    exit;
}

try {
    $pdo = new PDO("pgsql:host=localhost;port=5432;dbname=project", "postgres", "0", [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);

    $stmt = $pdo->prepare("SELECT 1 FROM intents WHERE user_id = :uid AND quote = :task_id");
    $stmt->execute(['uid' => $userId, 'task_id' => $taskId]);
    $hasIntent = $stmt->fetchColumn() ? true : false;

    echo json_encode(['hasIntent' => $hasIntent]);
} catch (Exception $e) {
    echo json_encode(['hasIntent' => false]);
}