<?php
session_start();
error_log("DEBUG: session_id=" . session_id());
error_log("DEBUG: session_name=" . session_name());
error_log("DEBUG: session_save_path=" . session_save_path());
error_log("DEBUG: ini session.use_cookies=" . ini_get('session.use_cookies'));
error_log("DEBUG: ini session.cookie_secure=" . ini_get('session.cookie_secure'));
error_log("DEBUG: ini session.cookie_samesite=" . ini_get('session.cookie_samesite'));

// 嘗試讀取 session 檔案（預設 php 的 file handler）
$savePath = session_save_path();
$sid = session_id();
if ($savePath && strpos($savePath, 'tcp://') === false) {
    // local filesystem
    $file = rtrim($savePath, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . 'sess_' . $sid;
    if (file_exists($file)) {
        error_log("DEBUG: session file exists: $file");
        error_log("DEBUG: session file contents: " . @file_get_contents($file));
    } else {
        error_log("DEBUG: session file NOT found at expected path: $file");
        // 列出目錄給你參考
        if (is_dir($savePath)) {
            $files = array_slice(scandir($savePath), -10);
            error_log("DEBUG: recent files in session_save_path: " . json_encode($files));
        }
    }
} else {
    error_log("DEBUG: session_save_path not local FS or empty: " . $savePath);
}

echo json_encode([
  'session_id' => session_id(),
  'session_name' => session_name(),
  'session_save_path' => session_save_path(),
  'session_keys' => array_keys($_SESSION)
]);
exit;