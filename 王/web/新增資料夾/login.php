<?php
session_start();
$data = json_decode(file_get_contents("php://input"), true);
$username = $data['username'];
$password = $data['password'];

$conn = pg_connect("host=localhost port=5432 dbname=project user=postgres password=0");
if (!$conn) {
  echo json_encode(["message" => "資料庫連線失敗"]);
  exit;
}

$result = pg_query_params($conn,
  "SELECT id, password_hash, role FROM users WHERE username=$1",
  [$username]
);
$row = pg_fetch_assoc($result);

if ($row && password_verify($password, $row['password_hash'])) {
  $_SESSION['user_id'] = $row['id'];
  $_SESSION['role'] = $row['role'];
  $_SESSION['username'] = $username;
  echo json_encode(["message" => "登入成功", "success" => true]);
} else {
  echo json_encode(["message" => "帳號或密碼錯誤", "success" => false]);
}
?>