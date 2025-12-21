<?php
$data = json_decode(file_get_contents("php://input"), true);
$username = $data['username'];
$password = $data['password'];
$role = $data['role'];

$conn = pg_connect("host=localhost port=5432 dbname=project user=postgres password=0");
if (!$conn) {
  echo json_encode(["message" => "資料庫連線失敗"]);
  exit;
}

$hash = password_hash($password, PASSWORD_DEFAULT);
$result = pg_query_params($conn,
  "INSERT INTO users (username, password_hash, role) VALUES ($1, $2, $3) ON CONFLICT (username) DO NOTHING",
  [$username, $hash, $role]
);

if (pg_affected_rows($result) > 0) {
  echo json_encode(["message" => "註冊成功"]);
} else {
  echo json_encode(["message" => "帳號已存在"]);
}
?>