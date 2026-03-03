<?php
include_once(__DIR__ . '/config.php');
include_once(__DIR__ . '/auth.php');

// Geçerli işlem (sayfa) parametresi
$aktif_islem = $_GET['islem'] ?? 'envanter'; // varsayılan: envanter

// log.json dosyasının son değiştirilme zamanını al
$log_dosyasi = 'logs.json';
$mod_zaman = file_exists($log_dosyasi) ? filemtime($log_dosyasi) : false;

// Şu anki zaman ile farkı hesapla
function zamanFarki($timestamp) {
    $fark = time() - $timestamp;
    if ($fark < 60) return $fark . " sn önce";
    $dakika = floor($fark / 60);
    $saniye = $fark % 60;
    return "{$dakika} dk {$saniye} sn önce";
}

// monitor-footer.php'de kullanılıyor
$log_bilgi = $mod_zaman ? zamanFarki($mod_zaman) : "Dosya bulunamadı";

// Yardımcı: aktif sınıfı verir
function aktifMi($sayfa) {
    global $aktif_islem;
    return $aktif_islem === $sayfa ? 'active' : '';
}
?>

<!-- Navigasyon Menüsü -->
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container-fluid">

    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
      <span class="navbar-toggler-icon"></span>
    </button>
	
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
			Açık Cihazları Kapat
		</a>	
	
	
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item">
          <a class="nav-link <?= aktifMi('et-agi-listele') ?>" href="?islem=et-agi-listele">Etkileşimli Tahtalar</a>
        </li>
        <li class="nav-item">
          <a class="nav-link <?= aktifMi('idare-agi-listele') ?>" href="?islem=idare-agi-listele">İdare Ağı</a>
        </li>
        <li class="nav-item">
          <a class="nav-link <?= aktifMi('oturumlar') ?>" href="?islem=oturumlar">Oturumlar</a>
        </li>
        <li class="nav-item">
          <a class="nav-link <?= aktifMi('anomaliler') ?>" href="?islem=logs">Anomaliler</a>
        </li>			
        <li class="nav-item">
          <a class="nav-link <?= aktifMi('logs') ?>" href="?islem=logs">Logs</a>
        </li>	
      </ul>
    </div>
  </div>
</nav>
