<?php
include_once(__DIR__ . '/config.php');
include_once(__DIR__ . '/auth.php');
?>
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ETA Monitör</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
	<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
    <link href="style.css" rel="stylesheet">
</head>
<body>
<?php
require("monitor-navbar.php");
if (isset($_GET['islem']))
    require("monitor-{$_GET['islem']}.php");
else
    require("monitor-et-agi-listele.php");

require("monitor-footer.php");
?>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
