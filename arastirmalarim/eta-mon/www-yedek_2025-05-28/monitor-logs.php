<?php

include_once(__DIR__ . '/config.php');
include_once(__DIR__ . '/auth.php');

// JSON dosyasını oku
$loglar = json_decode(file_get_contents('logs.json'), true);

// Kayıtları sondan başa çevir
$loglar = array_reverse($loglar);

function formatZaman($timestamp) {
    $simdi = time();
    $fark = $simdi - $timestamp;

    if ($fark < 3600) {
        $dakika = floor($fark / 60);
        $saniye = $fark % 60;

        $dakikaStr = $dakika > 0 ? $dakika . 'dk ' : '';
        $saniyeStr = $saniye . 'sn';
        return $dakikaStr . $saniyeStr . ' önce';
    } else {
        return date("Y-m-d H:i:s", $timestamp);
    }
}


// Seviye bazlı Bootstrap sınıfı belirle
function getRowClass($seviye) {
    switch (strtolower($seviye)) {
        case 'debug':
            return 'table-secondary';
        case 'bilgi':
            return 'table-success';
        case 'uyari':
            return 'table-warning';
        case 'hata':
            return 'table-danger';
        default:
            return '';
    }
}
?>
<!-- Modal -->
<div class="modal fade" id="cihazModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-xl" style="max-width: 90vw; height: 90vh;">
        <div class="modal-content" style="height: 90vh;">
            <div class="modal-header">
                <h5 class="modal-title">Cihaz Detayı</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Kapat"></button>
            </div>
            <div class="modal-body p-0">
                <iframe id="cihazIframe" src="" style="width: 100%; height: 100%; border: none;"></iframe>
            </div>
        </div>
    </div>
</div>

<table class="table table-bordered table-hover">
  <thead class="table-dark">
    <tr>
      <th>#</th>
      <th>Zaman</th>
      <th>Seviye</th>
      <th>Mesaj</th>
      <th>IP</th>
      <th>MAC</th>
    </tr>
  </thead>
  <tbody>
    <?php $sira = 1; ?>
    <?php foreach ($loglar as $log): ?>
      <tr class="<?= getRowClass($log['s']) ?>">
        <td><?= $sira++ ?></td>
        <td><?= formatZaman($log['z']) ?></td>
        <td><?= htmlspecialchars($log['s']) ?></td>
        <td><?= htmlspecialchars($log['l']) ?></td>
        <td><?= htmlspecialchars($log['i']) ?></td>
        <td><?= htmlspecialchars($log['m']) ?></td>
      </tr>
    <?php endforeach; ?>
  </tbody>
</table>

<script>
    document.querySelectorAll("table tbody tr").forEach(function(row) {
        const macCell = row.cells[5];
        const mac = macCell ? macCell.textContent.trim() : '';

        if (mac && mac !== '') {
            row.style.cursor = 'pointer';
            row.addEventListener('click', function () {
                const url = 'monitor-cihaz-goster.php?mac=' + encodeURIComponent(mac);
                const iframe = document.getElementById('cihazIframe');
                iframe.src = url;
                const modal = new bootstrap.Modal(document.getElementById('cihazModal'));
                modal.show();
            });
        }
    });
</script>

