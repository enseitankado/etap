<?php

if (!isset($_SESSION['authenticated'])) {
    $error = null;

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['password'])) {
        if ($_POST['password'] === $MASTER_PASSWORD) {
            $_SESSION['authenticated'] = true;
        } else {
            $error = "Hatalı parola!";
        }
    }

    if (!isset($_SESSION['authenticated'])) {
        ?>
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Giriş Yap</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {
                    background-color: #f8f9fa;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }
                .login-box {
                    width: 100%;
                    max-width: 400px;
                    padding: 2rem;
                    background: white;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                    border-radius: 10px;
                }
            </style>
        </head>
        <body>
            <div class="login-box">
                <h4 class="text-center mb-4">Yönetici Girişi</h4>
                <?php if ($error): ?>
                    <div class="alert alert-danger" role="alert">
                        <?= htmlspecialchars($error) ?>
                    </div>
                <?php endif; ?>
                <form method="post">
                    <div class="mb-3">
                        <label for="password" class="form-label">Parola</label>
                        <input type="password" class="form-control" id="password" name="password" placeholder="Parolanızı girin" required autofocus>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Giriş Yap</button>
                </form>
            </div>
        </body>
        </html>
        <?php
        exit;
    }
}