<?php


function cihaz_acik_kapali_zamanlarini_getir($timestamps)
{
    $uptimePeriods = [];
    $downtimePeriods = [];

    // Zaman damgalarını sıralayalım (bu genellikle sıralı gelir ama emin olmak için)
    sort($timestamps);

    // Önce ilk zaman damgasını "açık" olarak başlatıyoruz
    $currentStart = $timestamps[0];

    // Ardışık zaman damgalarını kontrol ediyoruz
    for ($i = 1; $i < count($timestamps); $i++) {
        $timeDifference = $timestamps[$i] - $timestamps[$i - 1];

        // Eğer iki zaman damgası arasındaki fark 2 dakikadan fazla ise bilgisayar kapalıdır
        if ($timeDifference > 300) {
            // Önceki zaman dilimi "açık" dönemi bitir
            $uptimePeriods[] = ['start' => $currentStart, 'end' => $timestamps[$i - 1]];

            // Kapalı dönemi başlat
            $downtimePeriods[] = ['start' => $timestamps[$i - 1], 'end' => $timestamps[$i]];

            // Yeni açık dönemi başlat
            $currentStart = $timestamps[$i];
        }
    }

    // Son açık dönemi de ekliyoruz
    $uptimePeriods[] = ['start' => $currentStart, 'end' => end($timestamps)];

    return ['uptime' => $uptimePeriods, 'downtime' => $downtimePeriods];
}

function cihaz_ag_ping_gecmisini_getir_arr($dosya_adi, $macAddress)
{
    // Geçmiş dosyasının yolu
    $gecmisDosyasi = 'betikler/' . $dosya_adi;

    // Dosyayı oku
    $jsonData = file_get_contents($gecmisDosyasi);

    // JSON verisini PHP dizisine dönüştür
    $data = json_decode($jsonData, true);

    // MAC adresini normalize et (sadece sayılar ve harfler kalacak)
    $macAddressNormalized = str_replace(":", "", strtolower($macAddress));

    // MAC adresi ile eşleşen veriyi bul ve timestamps dizisini döndür
    foreach ($data as $cihaz) {
        // Veritabanındaki MAC adresini de normalize et
        $cihazMacNormalized = str_replace(":", "", strtolower($cihaz['mac']));

        // Eğer MAC adresi eşleşirse, timestamps dizisini döndür
        if ($cihazMacNormalized === $macAddressNormalized) {
            return $cihaz['timestamps'];
        }
    }

    // Eğer MAC adresi bulunamazsa null döndür
    return null;
}


/*
	PHP'de bir string'i hostname kurallarına uygun hale getiren bir kod örneği aşağıda verilmiştir.
    Bu kod, verilen string'i aşağıdaki kurallara göre düzeltir:

	Harfler ve sayılar dışında yalnızca - (tire) karakterine izin verir.
	İlk ve son karakterler harf veya rakam olmalıdır.
	Küçük harfe dönüştürülür.
	Aralarındaki boşluklar kaldırılır.
*/
function hostname_duzelt($string)
{

    // Küçük harfe dönüştür
    $string = strtolower($string);

    // Geçerli karakterler: harfler, sayılar ve tire
    $string = preg_replace('/[^a-z0-9\-]/', '', $string);

    // Tirelerin başta veya sonda olmasına izin verme
    $string = trim($string, '-');

    return $string;
}

/*
 * 	MAC adresinden envanter kaydını getirir.

	Örneğin:
	  {
		"sira_no": 2,
		"envanter_no": "55.11.165.01.ET2.002",
		"seri_no": 675,
		"mac": "0009DF8AAD07",
		"sinif": "9F",
		"bina_kat": "A BLOK/2",
		"oda_no": 2
	  }

 */
function envanter_getir($mac)
{
    $jsonFile = __DIR__ . '/et-envanter.json';

    // JSON dosyasını oku
    if (!file_exists($jsonFile)) {
        return "Dosya bulunamadı!";
    }

    $jsonData = file_get_contents($jsonFile);
    $data = json_decode($jsonData, true);

    if ($data === null) {
        return "Geçersiz JSON!";
    }

    // MAC adresini ara
    foreach ($data as $entry) {
        if (isset($entry['mac']) && strtoupper($entry['mac']) == strtoupper($mac)) {
            return $entry;
        }
    }

    return null;
}

/*
	Gelen $env verisi örneğin:
	
	  {
		"sira_no": 2,
		"envanter_no": "55.11.165.01.ET2.002",
		"seri_no": 675,
		"mac": "0009DF8AAD07",
		"sinif": "9F",
		"bina_kat": "A BLOK/2",
		"oda_no": 2
	  }
*/
function envanterden_hostname_uret($env)
{

	if (is_null($env))
		return "kayitsiz-".rand(0,10000);

    $bina_kat = $env['bina_kat'];

    // Türkçe karakter dönüşümleri
    $bina_kat = strtr($bina_kat, [
        'Ç' => 'c', 'Ş' => 's', 'Ğ' => 'g', 'Ü' => 'u', 'İ' => 'i', 'Ö' => 'o',
        'ç' => 'c', 'ş' => 's', 'ğ' => 'g', 'ü' => 'u', 'ı' => 'i', 'ö' => 'o'
    ]);

    // Küçük harfe çevir
    $bina_kat = strtolower($bina_kat);

    // " blok/" gibi sabitleri sadeleştir
    $bina_kat = str_replace(' blok/', '-', $bina_kat); // "a blok/2" => "a-2"

    // Boşlukları ve kalan özel karakterleri tireyle değiştir
    $bina_kat = preg_replace('/[^a-z0-9]+/', '', $bina_kat); // sadece a-z, 0-9 kalır

    // Baştaki veya sondaki tireleri temizle
    $bina_kat = trim($bina_kat, '-');

    return hostname_duzelt('et-' . $bina_kat . '-' . strtolower($env['sinif']));

}


function mac_den_ip_getir($arananMac)
{
	
	$arananMac = strtolower($arananMac);
	
    // Kontrol edilecek dosya yolları
    $dosyaYollari = [
        'betikler/et-agi-aktif-cihazlar.json',
        'betikler/idare-agi-acik-cihazlar.json'
    ];


    foreach ($dosyaYollari as $dosyaYolu) {
        if (!file_exists($dosyaYolu)) {
            continue; // Dosya yoksa sıradakine geç
        }

        $json = file_get_contents($dosyaYolu);
        $cihazlar = json_decode($json, true);

        if (!is_array($cihazlar)) {
            continue; // Geçersiz JSON ise atla
        }

        foreach ($cihazlar as $cihaz) {
            if (isset($cihaz['mac']) && isset($cihaz['ip'])) {
                $mac = strtolower($cihaz['mac']);
                if ($mac === $arananMac) {
                    return $cihaz['ip'];
                }
            }
        }
    }

    return null; // Hiçbir dosyada bulunamadıysa
}


function aradakini_getir($string, $baslangic, $bitis)
{

    // Başlangıç ve bitiş stringlerinin bulunduğu konumları al
    $baslangicKonumu = strpos($string, $baslangic);
    $bitisKonumu = strpos($string, $bitis, $baslangicKonumu);

    // Başlangıç ve bitiş stringi bulunamazsa boş döndür
    if ($baslangicKonumu === false || $bitisKonumu === false) {
        return '';
    }

    // Başlangıç konumundan sonraki kısmı al (başlangıç stringini de dahil etme)
    $baslangicKonumu += strlen($baslangic);

    // Başlangıç ve bitiş arasındaki kısmı döndür
    return trim(substr($string, $baslangicKonumu, $bitisKonumu - $baslangicKonumu));
}

function ssh_komutu_calistir(string $hostip, string $command): string {
	
	include(__DIR__.'/config.php');
	
    $ssh_port = 22;
    $ssh_username = $ET_USERNAME;
    $ssh_password = $ET_PASSWORD;

    // Etkileşimli komutlar listesi
    $yasakli = ['top', 'less', 'nano', 'vi', 'vim', 'htop'];

    foreach ($yasakli as $yasak) {
        if (stripos($command, $yasak) !== false) {
            return "Hata: Bu komut etkileşimli olduğu için çalıştırılamaz: {$yasak}";
        }
    }

    if (!function_exists('ssh2_connect')) {
        return "Hata: SSH2 uzantısı yüklü değil.";
    }

    if (empty($hostip) || empty($command)) {
        return "Hata: IP adresi veya komut eksik.";
    }

    try {
        $connection = ssh2_connect($hostip, $ssh_port);
        if (!$connection) {
            return "Hata: SSH bağlantısı kurulamadı.";
        }

        if (!ssh2_auth_password($connection, $ssh_username, $ssh_password)) {
            return "Hata: Kimlik doğrulama başarısız. Kullanıcı adı/parola hatalı olabilir.";
        }

        $stream = ssh2_exec($connection, $command);
        if (!$stream) {
            return "Hata: Komut çalıştırılamadı.";
        }

        stream_set_blocking($stream, true);
        $result = stream_get_contents($stream);

        // Hata çıktısını da al
        $error_stream = ssh2_fetch_stream($stream, SSH2_STREAM_STDERR);
        stream_set_blocking($error_stream, true);
        $error_output = stream_get_contents($error_stream);

        $output = $result ?: '';
        if (!empty($error_output)) {
            $output .= "\n[stderr]: " . $error_output;
        }

        return trim($output);
    } catch (Exception $e) {
        return "Hata: " . $e->getMessage();
    }
}
?>