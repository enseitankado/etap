<?php

include_once(__DIR__ . '/config.php');
include_once(__DIR__ . '/auth.php');

set_time_limit(30); // Sonsuz yapma, sınırlı kalsın

if (file_exists('lib.php')) {
    include('lib.php');
}



// Bağlantı bilgileri
$ssh_host = $_GET['hostip'] ?? '';

if (isset($_GET['komut'])) {
	echo "$ssh_host IP adresli cihaza komut gönderildi.";
	echo "<br><br>";
	echo ssh_komutu_calistir($ssh_host, $_GET['komut']);	
	die();
}

$ssh_port = 22;
$ssh_username = $ET_USERNAME;
$ssh_password = $ET_PASSWORD; // SSH anahtarı kullanımı tavsiye edilir

$output = '';
$debug = '';
$command = '';
$executed = false;

// Komut geçmişi
if (!isset($_SESSION['command_history'])) {
    $_SESSION['command_history'] = [];
}

// POST isteği kontrolü
$debug .= "Request Method: " . $_SERVER['REQUEST_METHOD'] . "\n";

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['command'])) {
    $command = trim($_POST['command']);
    $debug .= "Command received: '{$command}'\n";

    if ($command !== '') {
        $executed = true;
        $_SESSION['command_history'][] = $command;

        if (!function_exists('ssh2_connect')) {
            $output .= "SSH2 uzantısı yüklü değil.\n";
        } elseif (empty($ssh_host)) {
            $output .= "Sunucu IP bilgisi eksik.\n";
        } else {
            try {
                $connection = ssh2_connect($ssh_host, $ssh_port);
                if (!$connection) {
                    $output .= "SSH bağlantısı kurulamadı.\n";
                } elseif (!ssh2_auth_password($connection, $ssh_username, $ssh_password)) {
                    $output .= "Kimlik doğrulama başarısız. Kullanıcı adı/parola hatalı olabilir.\n";
                } else {
                    // Etkileşimli olmayan komut filtrelemesi (geliştirilebilir)
                    $yasakli = ['top', 'less', 'nano', 'vi', 'vim', 'htop'];
                    foreach ($yasakli as $yasak) {
                        if (stripos($command, $yasak) !== false) {
                            $output .= "Bu komut etkileşimli olduğu için çalıştırılamaz: {$yasak}\n";
                            continue 1;
                        }
                    }

                    $stream = ssh2_exec($connection, $command);
                    if (!$stream) {
                        $output .= "Komut çalıştırılamadı.\n";
                    } else {
                        stream_set_blocking($stream, true);
                        $result = stream_get_contents($stream);

                        $error_stream = ssh2_fetch_stream($stream, SSH2_STREAM_STDERR);
                        stream_set_blocking($error_stream, true);
                        $error_output = stream_get_contents($error_stream);

                        $output .= $result ?: '';
                        if (!empty($error_output)) {
                            $output .= "\n[stderr]: " . $error_output;
                        }
                    }
                }
            } catch (Exception $e) {
                $output .= "Hata: " . $e->getMessage() . "\n";
            }
        }
    } else {
        $output .= "Boş komut gönderildi.\n";
    }
} else {
    $debug .= "POST verisi alınamadı.\n";
}

$command_history = array_slice($_SESSION['command_history'], -10);
?>
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SSH Terminali</title>
    <style>
        body {
            font-family: monospace;
            background-color: #2b2b2b;
            color: #f0f0f0;
            margin: 0;
            padding: 20px;
        }
        .terminal-container {
            width: 100%;
            max-width: 900px;
            margin: 0 auto;
            border: 1px solid #444;
            border-radius: 5px;
            background-color: #1e1e1e;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            height: 90vh;
        }
        .terminal-header {
            background-color: #333;
            padding: 8px 15px;
            border-bottom: 1px solid #444;
            border-radius: 5px 5px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .terminal-title {
            font-weight: bold;
            color: #ddd;
        }
        .terminal-controls span {
            height: 12px;
            width: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-left: 6px;
        }
        .control-close { background-color: #ff5f56; }
        .control-minimize { background-color: #ffbd2e; }
        .control-maximize { background-color: #27c93f; }

        .terminal-output {
            padding: 10px 15px;
            overflow-y: auto;
            flex-grow: 1;
            white-space: pre-wrap;
            line-height: 1.5;
        }
        .terminal-prompt {
            display: flex;
            border-top: 1px solid #444;
            padding: 10px 15px;
            background-color: #282828;
        }
        .terminal-prompt-text {
            color: #0f0;
            margin-right: 8px;
        }
        .terminal-input-form {
            display: flex;
            flex-grow: 1;
        }
        .terminal-input {
            flex-grow: 1;
            background-color: transparent;
            border: none;
            color: #fff;
            font-family: monospace;
            font-size: 14px;
            outline: none;
        }
        .history-item {
            margin-bottom: 15px;
            border-bottom: 1px dotted #444;
            padding-bottom: 10px;
        }
        .command {
            color: #0f0;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .output {
            color: #f0f0f0;
        }
        .connection-info {
            color: #888;
            font-size: 12px;
            margin-bottom: 10px;
            padding: 5px 0;
            border-bottom: 1px dotted #444;
        }
    </style>
</head>
<body>
<div class="terminal-container">
    <div class="terminal-header">
        <div class="terminal-controls">
            <span class="control-close"></span>
            <span class="control-minimize"></span>
            <span class="control-maximize"></span>
        </div>
        <div class="terminal-title">SSH Terminal - <?= htmlspecialchars($ssh_username . '@' . $ssh_host) ?></div>
    </div>

    <div class="terminal-output" id="terminalOutput">
        <div class="connection-info">
            Bağlantı: <?= htmlspecialchars($ssh_username . '@' . $ssh_host . ':' . $ssh_port) ?>
        </div>

        <?php if (!empty($debug)): ?>
            <div class="history-item">
                <div class="command">[DEBUG]</div>
                <div class="output"><?= nl2br(htmlspecialchars($debug)) ?></div>
            </div>
        <?php endif; ?>

        <?php foreach ($command_history as $index => $cmd): ?>
            <div class="history-item">
                <div class="command">$ <?= htmlspecialchars($cmd) ?></div>
                <?php if ($index === count($command_history) - 1 && $executed): ?>
                    <div class="output"><?= nl2br(htmlspecialchars($output)) ?></div>
                <?php endif; ?>
            </div>
        <?php endforeach; ?>
    </div>

    <div class="terminal-prompt">
        <div class="terminal-prompt-text">$</div>
        <form class="terminal-input-form" method="post" id="commandForm">
            <input type="text" name="command" class="terminal-input" id="commandInput" autofocus placeholder="Komut girin...">
            <input type="submit" style="position: absolute; left: -9999px;" tabindex="-1">
        </form>
    </div>
</div>

<script>
    document.addEventListener("DOMContentLoaded", function () {
        var outputDiv = document.getElementById('terminalOutput');
        outputDiv.scrollTop = outputDiv.scrollHeight;
        document.getElementById('commandInput').focus();
    });

    document.getElementById('commandForm').addEventListener('submit', function (e) {
        var commandInput = document.getElementById('commandInput');
        if (commandInput.value.trim() === '') {
            e.preventDefault();
        }
    });
</script>
</body>
</html>