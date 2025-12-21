<?php
session_start();
header('Content-Type: application/json; charset=utf-8');

echo json_encode([
  'user_id' => $_SESSION['user_id'] ?? null,
  'username' => $_SESSION['username'] ?? null
]);