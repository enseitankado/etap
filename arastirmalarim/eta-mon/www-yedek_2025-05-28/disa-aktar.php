<?php
// config.php içindeki değişkenleri yükle
require(__DIR__.'/config.php');

// HTTP üzerinden çağrılısa bitir
if (is_null($argc))
	die();

// Komut satırı argümanlarını al
if ($argc < 2) {
    fwrite(STDERR, "Kullanım: php cli.php DEGİSKEN_ADI\n");
    exit(1);
}

$degisken_adi = $argv[1];

// İstenen değişken varsa değerini yazdır
if (isset($$degisken_adi)) {
    echo $$degisken_adi;
} else {
    fwrite(STDERR, "Hata: Değişken '$degisken_adi' tanımlı değil.\n");
    exit(2);
}