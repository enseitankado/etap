<?php

include_once(__DIR__ . '/config.php');
include_once(__DIR__ . '/auth.php');


  include(__DIR__.'/lib.php');
  $envanter = json_decode(file_get_contents('idare-envanter.json'), true);
  $aktifCihazlar = json_decode(file_get_contents('betikler/idare-agi-aktif-cihazlar.json'), true);
  foreach ($aktifCihazlar as $cihaz)
    $aktifMacToIp[strtolower($cihaz['mac'])] = $cihaz['ip'];
?>
<div style="margin:20px;">
<input type="text" id="aramaKutusu" class="form-control my-3" placeholder="Tabloda ara...">

<table class="table table-bordered table-striped table-hover sortable>
  <thead class="table-dark">
    <tr>
      <th onclick="sortTable(0)">Sıra No</th>
	  <th onclick="sortTable(1)">Bina/Kat</th>
      <th onclick="sortTable(2)">Oda No</th>
	  <th onclick="sortTable(3)">Sınıfı</th>
	  <th onclick="sortTable(4)">Hostname</th>
      <th onclick="sortTable(5)">Aktif IP</th>
	  <th onclick="sortTable(6)">MAC Adresi</th>	
      <th onclick="sortTable(7)">Seri No</th>
	  <th onclick="sortTable(8)">Envanter No</th>     
        
    </tr>
  </thead>
  <tbody id="envanterTabloGovdesi">
    <?php foreach ($envanter as $cihaz): ?>
      <?php
	    $cihaz['mac'] = strtolower($cihaz['mac']);
        $aktifMi = array_key_exists($cihaz['mac'], $aktifMacToIp);
        $aktifIp = $aktifMi ? $aktifMacToIp[$cihaz['mac']] : '';
        $rowClass = $aktifMi ? 'table-success' : '';
		if ($aktifMi)
			$aktif_sayisi++;
		else
			$pasif_sayisi--;		
      ?>
        <tr class="<?= $rowClass ?>" data-ip="<?= htmlspecialchars($aktifIp) ?>">
        <td><?= htmlspecialchars($cihaz['sira_no']) ?></td>
        <td><?= htmlspecialchars($cihaz['bina_kat']) ?></td>
		<td><?= htmlspecialchars($cihaz['oda_no']) ?></td>
		<td><?= htmlspecialchars($cihaz['sinif']) ?></td>
		<td><?= envanterden_hostname_uret($cihaz); ?></td>
		<td><?= htmlspecialchars($aktifIp) ?></td>
		<td><?= htmlspecialchars($cihaz['mac']) ?></td>		
        <td><?= htmlspecialchars($cihaz['seri_no']) ?></td>
		<td><?= htmlspecialchars($cihaz['envanter_no']) ?></td>  
      </tr>
    <?php endforeach; ?>
  </tbody>
</table>

<!-- Modal -->
<div class="modal fade" id="macModal" tabindex="-1" aria-labelledby="macModalLabel" aria-hidden="true">
    <div class="modal-dialog" id="macModalDialog">
        <div class="modal-content" style="height: 100%;">
            <div class="modal-header">
                <h5 class="modal-title" id="macModalLabel">Cihaz Detayı</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Kapat"></button>
            </div>
            <div class="modal-body p-0">
                <iframe id="macModalIframe" src="" style="width:100%; height:100%; border:0;"></iframe>
            </div>
        </div>
    </div>
</div>

<?php
// Aktif/Pasif sayacı için başlangıç
$aktif_sayisi = 0;
$pasif_sayisi = 0;

// Cihazları işlerken sayıları sayacağız (bu satırı cihaz döngüsünden önce koy)
foreach ($envanter as $cihaz) {
    if (array_key_exists(strtolower($cihaz['mac']), $aktifMacToIp)) {
        $aktif_sayisi++;
    } else {
        $pasif_sayisi++;
    }
}

// Dosya güncelleme zamanını hesapla
$dosyaYolu = 'betikler/et-agi-aktif-cihazlar.json';
$dosyaZaman = filemtime($dosyaYolu);
$simdi = time();
$fark_saniye = $simdi - $dosyaZaman;

if ($fark_saniye < 60) {
    $guncellemeMetni = $fark_saniye . ' saniye önce tarandı';
} elseif ($fark_saniye < 3600) {
    $guncellemeMetni = floor($fark_saniye / 60) . ' dakika önce tarandı';
} elseif ($fark_saniye < 86400) {
    $guncellemeMetni = floor($fark_saniye / 3600) . ' saat önce tarandı';
} else {
    $guncellemeMetni = floor($fark_saniye / 86400) . ' gün önce tarandı';
}
?>

<?php
    $envanter_sayisi = count($envanter);
    $agdaki_acik_cihaz_sayisi = count($aktifCihazlar);
    $envanter_acik_sayisi = $aktif_sayisi;
    $envanter_kapali_sayisi = $pasif_sayisi;
?>
<div class="mt-3">
    <div class="alert alert-info d-flex justify-content-between align-items-center">
        <div>

            <strong>Açık ET sayısı:</strong> <?= $envanter_acik_sayisi ?> |
            <strong>Kapalı ET sayısı:</strong> <?= $envanter_kapali_sayisi ?> |
            <strong>Diğer açık cihazlar:</strong> <?= $agdaki_acik_cihaz_sayisi-$envanter_acik_sayisi ?>

        </div>
        <div><small class="text-muted"><?= $guncellemeMetni ?></small></div>
    </div>
</div>

<script>
    document.querySelectorAll('#envanterTabloGovdesi tr').forEach(row => {        

		row.style.cursor = 'pointer';
		row.addEventListener('click', () => {
			const mac = row.children[6].textContent.trim();
			const iframe = document.getElementById('macModalIframe');
			iframe.src = 'monitor-cihaz-goster.php?mac=' + encodeURIComponent(mac);
			const modal = new bootstrap.Modal(document.getElementById('macModal'));
			modal.show();
		});

    });
</script>

<script>
// Tablo sıralama
let sortDirection = {};

function sortTable(columnIndex) {
  const table = document.querySelector(".sortable");
  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("tr"));
  const ascending = !sortDirection[columnIndex];

  rows.sort((a, b) => {
    const aText = a.children[columnIndex].textContent.trim();
    const bText = b.children[columnIndex].textContent.trim();

    const aNum = parseFloat(aText.replace(',', '.'));
    const bNum = parseFloat(bText.replace(',', '.'));

    const isNumeric = !isNaN(aNum) && !isNaN(bNum);

    if (isNumeric) {
      return ascending ? aNum - bNum : bNum - aNum;
    } else {
      return ascending
        ? aText.localeCompare(bText, 'tr')
        : bText.localeCompare(aText, 'tr');
    }
  });

  sortDirection[columnIndex] = ascending;

  // Sıralanmış satırları yeniden ekle
  tbody.innerHTML = '';
  rows.forEach(row => tbody.appendChild(row));
}

// Filtreleme
document.getElementById('aramaKutusu').addEventListener('keyup', function () {
  const aranan = this.value.toLowerCase();
  const rows = document.querySelectorAll('#envanterTabloGovdesi tr');
  rows.forEach(row => {
    const metin = row.textContent.toLowerCase();
    row.style.display = metin.includes(aranan) ? '' : 'none';
  });
});
</script>

</div>