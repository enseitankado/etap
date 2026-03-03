<?php
include_once(__DIR__ . '/config.php');
include_once(__DIR__ . '/auth.php');
include(__DIR__ . '/lib.php');

$mac_adresi = strtolower($_GET['mac']) ?? '';
$acik_kapali_arr = json_decode(file_get_contents(__DIR__ . '/betikler/et-agi-acik-kapali.json'), true);
if (!isset($acik_kapali_arr[$mac_adresi]))
    die("$mac_adresi MAC adresi bulunamadı.");

$env = envanter_getir($mac_adresi);
$zamanlar = $acik_kapali_arr[$mac_adresi];

// Tarih bazında gruplama yap
$gunluk_veri = [];

foreach ($zamanlar as $kayit) {
    $baslangic = $kayit['s'];
    $bitis = $kayit['e'];
    $gun_baslangic = date('Y-m-d', $baslangic);
    $gun_bitis = date('Y-m-d', $bitis);

    // Tek günlük kayıtlar
    if ($gun_baslangic === $gun_bitis) {
        $gunluk_veri[$gun_baslangic][] = [$baslangic, $bitis];
    } else {
        // Çok günlü kayıtları ayır
        $gun_ilk = strtotime($gun_baslangic . ' 00:00:00') + 86400;
        $gun_son = strtotime($gun_bitis . ' 00:00:00');

        $gunluk_veri[$gun_baslangic][] = [$baslangic, $gun_ilk - 1];
        $gunluk_veri[$gun_bitis][] = [$gun_son, $bitis];
    }
}
$gunluk_veri = array_reverse($gunluk_veri);
$hostname = strtoupper(envanterden_hostname_uret($env));
// HTML ve Bootstrap çıktısı
?>
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Zaman Çizelgesi</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
	body {
		margin: 0;
		padding: 0;
	}

	.container {
		padding-left: 50px;
		padding-right: 50px;
		max-width: 100%;
		width: 100%;
	}

	.timeline {
		display: flex;
		position: relative;
		border: 1px solid #ccc;
		margin-bottom: 0;
		width: 100%;
	}

	.saat {
		flex: 1;
		height: 30px;
		border-right: 1px solid #ddd;
		position: relative;
	}

	.mesai-dis {
		background-color: #e0e0e0;
		position: absolute;
		top: 0;
		height: 100%;
		z-index: 0;
	}

	.aktif-zaman {
		position: absolute;
		height: 100%;
		background-color: #28a745;
		z-index: 1;
		opacity: 0.8;
	}

	.tarih {
		font-weight: bold;
		margin-top: 0;
		width: 100%;
		text-align: left;
	}
		
    html, body {
        margin: 0;
        padding: 0;
        height: 100%;
        width: 100%;
		margin-bottom:50px;
		padding-bottom:50px;
    }

    </style>
</head>

<body class="container mt-4">

<div class="row mb-4">
    <!-- İlk Tablo -->
    <div class="col-md-6">
        <table class="table table-sm table-bordered table-striped">
            <tbody>
            <?php foreach ($env as $key => $value): ?>
                <tr>
                    <th class="text-capitalize"><?= htmlspecialchars(str_replace('_', ' ', $key)) ?></th>
                    <td><?= htmlspecialchars($value) ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </div>
    
	<!-- İkinci Tablo -->
    <div class="col-md-6">
	
		<?php
			$ip = mac_den_ip_getir($env['mac']); // Veya null olabilir
		?>

		<!-- SSH Terminal Butonu -->
		<a 
			href="<?= $ip ? 'cmd.php?hostip=' . urlencode($ip) : '#' ?>" 
			class="btn btn-success d-inline-flex align-items-center <?= is_null($ip) ? 'disabled' : '' ?>"
			target="<?= $ip ? '_blank' : '_self' ?>"
			<?= is_null($ip) ? 'aria-disabled="true" tabindex="-1"' : '' ?>
		>
			<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
				 class="bi bi-terminal me-2" viewBox="0 0 16 16">
				<path d="M1 2a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1H1zm14 1v10H1V3h14zM2.5 5.5 4 7l-1.5 1.5L3 9l2-2-2-2-.5.5zm2.5 5.5a.5.5 0 0 1 0-1h5a.5.5 0 0 1 0 1H5z"/>
			</svg>
			Terminal
		</a>
		
		<!-- Kapat -->
		<a 
			href="<?= $ip ? 'cmd.php?hostip=' . urlencode($ip).'&komut='.urlencode('echo "tankado" | sudo -S init 0') : '#' ?>" 
			class="btn btn-danger d-inline-flex align-items-center <?= is_null($ip) ? 'disabled' : '' ?>"
			target="<?= $ip ? '_blank' : '_self' ?>"
			<?= is_null($ip) ? 'aria-disabled="true" tabindex="-1"' : '' ?>
			onclick="return confirm('<?= $hostname ?> cihazını kapatmak istediğinize emin misiniz?');"
		>
			<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
				 class="bi bi-toggle-off me-2" viewBox="0 0 16 16">
				<path d="M11 5a3 3 0 1 1 0 6H5a3 3 0 0 1 0-6h6zm0-1H5a4 4 0 1 0 0 8h6a4 4 0 1 0 0-8z"/>
			</svg>
			Cihazı Kapat
		</a>
		
		<!-- Kullanıcı Sil -->
		<a 
			href="<?= $ip ? 'cmd.php?hostip=' . urlencode($ip).'&komut='.urlencode("echo 'tankado' | sudo -S deluser ebaqr") : '#' ?>" 
			class="btn btn-danger d-inline-flex align-items-center <?= is_null($ip) ? 'disabled' : '' ?>"
			target="<?= $ip ? '_blank' : '_self' ?>"
			<?= is_null($ip) ? 'aria-disabled="true" tabindex="-1"' : '' ?>
			onclick="return confirm('<?= $hostname ?> cihazı üzerindeki ebaqr kullanıcı hesabını silmek istediğinize emin misiniz?');"
		>
			<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
				 class="bi bi-person-x-fill me-2" viewBox="0 0 16 16">
				<path d="M11 6a3 3 0 1 0-6 0 3 3 0 0 0 6 0z"/>
				<path fill-rule="evenodd" d="M0 13a5 5 0 0 1 10 0H0z"/>
				<path fill-rule="evenodd" d="M14.854 5.854a.5.5 0 0 1-.708 0L13 4.707 11.854 5.854a.5.5 0 1 1-.708-.708L12.293 4 11.146 2.854a.5.5 0 1 1 .708-.708L13 3.293l1.146-1.147a.5.5 0 0 1 .708.708L13.707 4l1.147 1.146a.5.5 0 0 1 0 .708z"/>
			</svg>
			ebaqr kullanıcısını sil
		</a>
	


		
    </div>
</div>

<h3 class="mb-4"><?= htmlspecialchars($hostname) ?> için kullanım çizelgesi</h3>

<?php
$gunler = [
    'Monday'    => 'Pazartesi',
    'Tuesday'   => 'Salı',
    'Wednesday' => 'Çarşamba',
    'Thursday'  => 'Perşembe',
    'Friday'    => 'Cuma',
    'Saturday'  => 'Cumartesi',
    'Sunday'    => 'Pazar',
];
?>

<?php foreach ($gunluk_veri as $tarih => $kayitlar): ?>
	<?php $tarih_gunu = $gunler[date("l", strtotime($tarih))];?>
    <div class="tarih"><?= $tarih ?> <?= $tarih_gunu ?></div>
    <div class="timeline">
	
        <?php for ($i = 0; $i < 24; $i++): ?>
            <div class="saat">
                <div style="position:absolute;bottom:0;font-size:10px;left:2px;color:#ccc;"><?= str_pad($i, 2, '0', STR_PAD_LEFT) ?>:00                    
                </div>
            </div>
        <?php endfor; ?>

        <?php
        // Mesai dışı saatleri (00:00-08:00 ve 17:00-24:00)
        $mesai_dis_saatleri = [[0, 8], [17, 24]];
        foreach ($mesai_dis_saatleri as [$bas, $bit]) {
            $sol = ($bas / 24) * 100;
            $genislik = (($bit - $bas) / 24) * 100;
            echo "<div class='mesai-dis' style='left:$sol%; width:$genislik%;'></div>";
        }

        // Aktif zamanları yerleştir
        foreach ($kayitlar as [$baslangic, $bitis]) {
            $gun_basi = strtotime("$tarih 00:00:00");
            $gun_sonu = strtotime("$tarih 23:59:59");

            // Kesin sınırla
            $gercek_bas = max($baslangic, $gun_basi);
            $gercek_bit = min($bitis, $gun_sonu);

            $sure = $gun_sonu - $gun_basi;
            $sol = (($gercek_bas - $gun_basi) / $sure) * 100;
            $genislik = (($gercek_bit - $gercek_bas) / $sure) * 100;

            $acilis = date('Y/m/d H:i:s', $baslangic);
            $kapanis = date('Y/m/d H:i:s', $bitis);
            $aciklama = "Açılış: $acilis\nKapanış: $kapanis";
			$kullanici = et_a_k_zamanindan_kullanici_getir($baslangic, $bitis, $mac_adresi);
			if (!is_null($kullanici))
				$aciklama .= "\nKullanıcı: $kullanici";
			
            echo "<div class='aktif-zaman' style='left:$sol%; width:$genislik%;' data-bs-toggle='tooltip' title=\"" . htmlspecialchars($aciklama) . "\"></div>";
        }
        ?>
    </div>
<?php endforeach; ?>

<?php

function et_a_k_zamanindan_kullanici_getir($et_acilis, $et_kapanis, $mac_adresi) {
	
	$mac_adresi = strtolower($mac_adresi);
	
	// JSON verisini örnek olarak alalım (bu veriyi dosyadan veya başka bir kaynaktan okuyabilirsiniz)
    $jsonData = file_get_contents("kullanicilarin-oturum-zamanlari.json");
	
    
	// JSON verisini decode et
    $data = json_decode($jsonData, true); 
    
    // Tolerans (300 saniye)
    $tolerance = 300;
    
    // Kullanıcılar üzerinde döngü
    foreach ($data as $user => $acilis_kapanis) {
		
		// Mac adresi varsa acilis zamanlarini al
		if (isset($acilis_kapanis['a'][$mac_adresi]))  {

			$oturum_acilis_zamanlari = $acilis_kapanis['a'][$mac_adresi];
			foreach($oturum_acilis_zamanlari as $o_acilis) {
				
				if ($o_acilis > $et_acilis and $o_acilis < $et_kapanis)
					return $user;
			}
		}		
    }
    
    return null; // Hiçbir eşleşme bulunmazsa null döndür
}

?>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
    const tooltipTetikleyiciler = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTetikleyiciler.forEach(el => new bootstrap.Tooltip(el));
</script>

</body>
</html>
