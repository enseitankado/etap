<?php

// Komut satırı argümanları kontrolü
if ($argc < 4) {
    echo "Kullanım: php acik-kapali-ozetle.php <girdi_dosyasi> <cikti_dosyasi> <maks_fark_saniye>\n";
    exit(1);
}

// Argümanları al
$input_file = $argv[1];
$output_file = $argv[2];
$max_diff = intval($argv[3]);

if (!file_exists($input_file)) {
    die("Girdi dosyası bulunamadı: $input_file\n");
}

$raw_data = file_get_contents($input_file);
$device_data = json_decode($raw_data, true);

if (!$device_data) {
    die("Geçersiz JSON verisi.\n");
}

$output = [];

// Her cihaz için işlem
foreach ($device_data as $device) {
    $mac = $device['mac'];
    $timestamps = $device['timestamps'];

    if (empty($timestamps)) continue;

    sort($timestamps);
    $acik_araliklar = [];
    $start = $timestamps[0];
    $prev = $timestamps[0];

    foreach (array_slice($timestamps, 1) as $ts) {
        if ($ts - $prev <= $max_diff) {
            $prev = $ts;
        } else {
            $acik_araliklar[] = [
                's' => $start,
                'e' => $prev
            ];
            $start = $ts;
            $prev = $ts;
        }
    }

    // Son aralık
    $acik_araliklar[] = [
        's' => $start,
        'e' => $prev
    ];

    $output[$mac] = $acik_araliklar;
}

// Çıkışı JSON dosyasına yaz
file_put_contents($output_file, json_encode($output, JSON_PRETTY_PRINT));
echo "Açık zaman aralıkları başarıyla '$output_file' dosyasına yazıldı.\n";
