<?php
include_once(__DIR__ . '/config.php');
include_once(__DIR__ . '/auth.php');

$kullanici_idler_json = file_get_contents('kullanicilarin-idleri.json');
$kullanici_idler = json_decode($kullanici_idler_json, true);

$kullanici_oturumlar_json = file_get_contents('kullanicilarin-oturum-zamanlari.json');
$kullanici_oturumlar = json_decode($kullanici_oturumlar_json, true);

$envanter_arr = json_decode(file_get_contents('et-envanter.json'), true);

function mac_den_gorunur_ad_getir($mac, $envanter_arr) {

    $mac = strtoupper($mac);

	foreach($envanter_arr as $env) 
		if ($env['mac'] == $mac)
			return $env['bina_kat'].' - '.$env['sinif'];

	return $mac;
}

function format_sure($saniye) {
    if ($saniye === null || $saniye < 0) return 'N/A';
    $saat = floor($saniye / 3600);
    $dakika = floor(($saniye % 3600) / 60);
    $sn = $saniye % 60;
    return sprintf('%02d:%02d:%02d', $saat, $dakika, $sn);
}

function slug_to_name($slug) {
    $parts = explode('-', $slug);
    if (end($parts) === 'qr') array_pop($parts);
    return ucwords(implode(' ', $parts));
}

$gosterilecek_veriler = [];
$sira_no = 0;
$BIRLESTIRME_ESIGI_SANIYE = 2 * 60; // 4 dakika olarak güncellendi

if ($kullanici_idler && $kullanici_oturumlar) {
    foreach ($kullanici_idler as $user_slug => $user_id_val) {
        $sira_no++;
        $kullanici_adi = slug_to_name($user_slug);

        // 1. ADIM: BİREYSEL OTURUMLARI OLUŞTURMA
        $gecici_bireysel_oturumlar_kullanici_icin = [];
        if (isset($kullanici_oturumlar[$user_slug])) {
            $girisler_tum_maclar = $kullanici_oturumlar[$user_slug]['a'] ?? [];
            $cikislar_tum_maclar = $kullanici_oturumlar[$user_slug]['k'] ?? [];
            $tum_mac_adresleri = array_unique(array_merge(array_keys($girisler_tum_maclar), array_keys($cikislar_tum_maclar)));

            foreach ($tum_mac_adresleri as $mac) {
                $mac_giris_zamanlari = $girisler_tum_maclar[$mac] ?? [];
                if (!is_array($mac_giris_zamanlari)) $mac_giris_zamanlari = [];
                sort($mac_giris_zamanlari, SORT_NUMERIC);

                $mac_cikis_zamanlari_orijinal = $cikislar_tum_maclar[$mac] ?? [];
                if (!is_array($mac_cikis_zamanlari_orijinal)) $mac_cikis_zamanlari_orijinal = [];
                sort($mac_cikis_zamanlari_orijinal, SORT_NUMERIC);
                
                $kullanilabilir_cikislar_bu_mac_icin = $mac_cikis_zamanlari_orijinal;

                foreach ($mac_giris_zamanlari as $giris_zamani) {
                    $bulunan_cikis_zamani = null;
                    $en_uygun_cikis_idx_global = -1;

                    foreach ($kullanilabilir_cikislar_bu_mac_icin as $idx => $cikis_zamani_aday) {
                        if ($cikis_zamani_aday > $giris_zamani) {
                            if ($bulunan_cikis_zamani === null || $cikis_zamani_aday < $bulunan_cikis_zamani) {
                                $bulunan_cikis_zamani = $cikis_zamani_aday;
                                $en_uygun_cikis_idx_global = $idx;
                            }
                        }
                    }
                    
                    $sure = null;
                    if ($bulunan_cikis_zamani !== null) {
                        $sure = $bulunan_cikis_zamani - $giris_zamani;
                        if ($en_uygun_cikis_idx_global !== -1) {
                            unset($kullanilabilir_cikislar_bu_mac_icin[$en_uygun_cikis_idx_global]);
                             // Indeksleri yeniden düzenlemek için array_values kullanılabilir,
                             // özellikle çok fazla eleman varsa ve unset sonrası performans önemliyse.
                             // $kullanilabilir_cikislar_bu_mac_icin = array_values($kullanilabilir_cikislar_bu_mac_icin);
                        }
                    }
                    $gecici_bireysel_oturumlar_kullanici_icin[] = [
                        'mac' => $mac,
                        'giris' => $giris_zamani,
                        'cikis' => $bulunan_cikis_zamani,
                        'sure' => ($sure !== null && $sure < 0) ? null : $sure
                    ];
                }
            }
        }
        
        // 2. ADIM: "DEVAM EDİYOR" OTURUMLARINI FİLTRELEME VE AYNI ANDA BAŞLAYANLARI DÜZENLEME
        $oturumlar_mac_gore_gruplu_ilk_hali = [];
        foreach ($gecici_bireysel_oturumlar_kullanici_icin as $oturum) {
            if ($oturum['giris'] === null) continue; // Giriş zamanı olmayanları atla
            $oturumlar_mac_gore_gruplu_ilk_hali[$oturum['mac']][] = $oturum;
        }

        $kullanici_icin_islenmis_liste = []; // Filtrelenmiş ve ilk düzenlemesi yapılmış liste
        foreach ($oturumlar_mac_gore_gruplu_ilk_hali as $mac => $mac_oturumlari_listesi) {
            $tamamlanmis_bu_mac = [];
            $devam_eden_bu_mac = [];

            foreach ($mac_oturumlari_listesi as $oturum) {
                if ($oturum['cikis'] !== null && $oturum['cikis'] > $oturum['giris']) {
                    $tamamlanmis_bu_mac[] = $oturum;
                } else if ($oturum['cikis'] === null) { // Giriş var, çıkış yok
                    $devam_eden_bu_mac[] = $oturum;
                }
            }

            usort($tamamlanmis_bu_mac, function($a, $b) { return $a['giris'] <=> $b['giris']; });
            usort($devam_eden_bu_mac, function($a, $b) { return $a['giris'] <=> $b['giris']; });

            // "Devam ediyor"ları filtrele
            $korunacak_devam_edenler = [];
            foreach ($devam_eden_bu_mac as $devam_oturum) {
                $kapsaniyor = false;
                foreach ($tamamlanmis_bu_mac as $tamam_oturum) {
                    if ($devam_oturum['giris'] >= $tamam_oturum['giris'] && $devam_oturum['giris'] < $tamam_oturum['cikis']) {
                        $kapsaniyor = true;
                        break;
                    }
                }
                if (!$kapsaniyor) $korunacak_devam_edenler[] = $devam_oturum;
            }
            
            // 2. ADIM SONRASI EK DÜZENLEME: Aynı anda başlayan tamamlanmışlardan sadece en geç biteni tut
            $final_tamamlanmis_bu_mac = [];
            if (!empty($tamamlanmis_bu_mac)) {
                // Giriş zamanına, sonra çıkış zamanına (azalan, yani en geç biten önce) göre sırala
                usort($tamamlanmis_bu_mac, function($a, $b) {
                    if ($a['giris'] == $b['giris']) {
                        // Çıkış null ise en sona at (veya en başa, tutarlılık önemli)
                        if ($a['cikis'] === null && $b['cikis'] === null) return 0;
                        if ($a['cikis'] === null) return 1; // a null, b değilse, a sona
                        if ($b['cikis'] === null) return -1; // b null, a değilse, b sona
                        return $b['cikis'] <=> $a['cikis']; // İkisi de null değil, büyük olan önce
                    }
                    return $a['giris'] <=> $b['giris'];
                });

                $son_eklenen_giris_zamani = null;
                foreach ($tamamlanmis_bu_mac as $oturum) {
                    // Eğer bu giriş zamanı daha önce eklenmediyse VEYA bu, o giriş zamanı için ilk (ve en uzun) oturumsa
                    if ($oturum['giris'] !== $son_eklenen_giris_zamani) {
                        $final_tamamlanmis_bu_mac[] = $oturum;
                        $son_eklenen_giris_zamani = $oturum['giris'];
                    }
                }
            }
            // İşlenmiş listeyi topla
            $kullanici_icin_islenmis_liste = array_merge($kullanici_icin_islenmis_liste, $final_tamamlanmis_bu_mac, $korunacak_devam_edenler);
        }
        
        // 3. ADIM: OTURUM BİRLEŞTİRME (GÜNCELLENMİŞ MANTIK)
        $oturumlar_mac_bazli_birlesecek = [];
        foreach ($kullanici_icin_islenmis_liste as $oturum) {
            $oturumlar_mac_bazli_birlesecek[$oturum['mac']][] = $oturum;
        }
        
        $son_oturumlar_kullanici_icin = []; 
        foreach ($oturumlar_mac_bazli_birlesecek as $mac => $mac_oturumlari) {
            if (empty($mac_oturumlari)) continue;
            usort($mac_oturumlari, function ($a, $b) { // Başlangıç zamanına göre sırala
                 if ($a['giris'] == $b['giris']) { // Aynı başlangıçsa, bitişe göre sırala (önemsiz olabilir ama tutarlı)
                    if ($a['cikis'] === null && $b['cikis'] === null) return 0;
                    if ($a['cikis'] === null) return 1;
                    if ($b['cikis'] === null) return -1;
                    return $a['cikis'] <=> $b['cikis'];
                 }
                 return $a['giris'] <=> $b['giris'];
            });

            $birlestirilmis_mac_oturumları = [];
            $aktif_oturum = array_shift($mac_oturumlari); // İlk oturumu aktif olarak al

            foreach ($mac_oturumlari as $mevcut_oturum) {
                $birlesme_oldu = false;
                if ($aktif_oturum['cikis'] !== null && $mevcut_oturum['giris'] !== null) {
                    // Koşul 1: Örtüşme var mı? (mevcut, aktifin bitiminden önce veya aynı anda başlıyor)
                    $ortusme_var = ($mevcut_oturum['giris'] <= $aktif_oturum['cikis']);
                    
                    // Koşul 2: Örtüşme yoksa, ardışık ve aradaki fark eşikten küçük mü?
                    $ardisik_yakin = (!$ortusme_var && ($mevcut_oturum['giris'] - $aktif_oturum['cikis'] < $BIRLESTIRME_ESIGI_SANIYE));

                    if ($ortusme_var || $ardisik_yakin) {
                        // Birleştir
                        if ($mevcut_oturum['cikis'] === null) { // Mevcut devam ediyordevam ediyorsa, birleşen de devam eder
                            $aktif_oturum['cikis'] = null;
                        } elseif ($aktif_oturum['cikis'] !== null) { // İkisi de tamamlanmışsa, en geç biteni al
                            $aktif_oturum['cikis'] = max($aktif_oturum['cikis'], $mevcut_oturum['cikis']);
                        }
                        // Eğer aktif_oturum zaten 'devam ediyor' ise (cikis === null), mevcut_oturum'un çıkışı ne olursa olsun 'devam ediyor' kalır.
                        // Bu durum yukarıdaki ($mevcut_oturum['cikis'] === null) koşulu ile ele alınır.
                        
                        $birlesme_oldu = true;
                    }
                } elseif ($aktif_oturum['cikis'] === null && $mevcut_oturum['giris'] !== null) { 
                    // Aktif devam ediyor, mevcutun girişi var. Eğer mevcut, aktifin başlangıcından sonraysa birleşir.
                    // Bu durum genelde oluşmaz çünkü devam edenler sona kalır veya zaten filtrelenir.
                    // Ama yine de bir kontrol: Eğer aktif devam ediyorsa ve mevcut ondan sonraysa birleşebilir.
                    // Şimdilik bu senaryoyu karmaşıklaştırmamak adına pas geçiyorum, ilk koşul bloğu ana mantığı kapsar.
                }


                if (!$birlesme_oldu) {
                    if ($aktif_oturum['giris'] !== null) { // Süreyi yeniden hesapla (birleşme olmasa bile, önceki adımdan gelebilir)
                         if($aktif_oturum['cikis'] !== null) {
                            $aktif_oturum['sure'] = $aktif_oturum['cikis'] - $aktif_oturum['giris'];
                            if($aktif_oturum['sure'] < 0) $aktif_oturum['sure'] = null;
                         } else {
                            $aktif_oturum['sure'] = null;
                         }
                    }
                    $birlestirilmis_mac_oturumları[] = $aktif_oturum;
                    $aktif_oturum = $mevcut_oturum;
                }
            }
            
            // Son aktif oturumu da ekle ve süresini hesapla
            if ($aktif_oturum['giris'] !== null) {
                 if($aktif_oturum['cikis'] !== null) {
                    $aktif_oturum['sure'] = $aktif_oturum['cikis'] - $aktif_oturum['giris'];
                    if($aktif_oturum['sure'] < 0) $aktif_oturum['sure'] = null;
                 } else {
                    $aktif_oturum['sure'] = null;
                 }
            }
            $birlestirilmis_mac_oturumları[] = $aktif_oturum;
            $son_oturumlar_kullanici_icin = array_merge($son_oturumlar_kullanici_icin, $birlestirilmis_mac_oturumları);
        }
        
        usort($son_oturumlar_kullanici_icin, function ($a, $b) { return $a['giris'] <=> $b['giris']; });

        $gosterilecek_veriler[] = [
            'sira_no' => $sira_no,
            'adi' => $kullanici_adi,
            'id' => $user_id_val,
            'oturumlar' => $son_oturumlar_kullanici_icin
        ];
    }
}
?>
<div class="container mt-5">
	
	<?php if (empty($gosterilecek_veriler)): ?>
		<div class="alert alert-warning" role="alert">Gösterilecek kullanıcı verisi bulunamadı.</div>
	<?php else: ?>
		<div class="accordion" id="kullaniciListesiAccordion">
			<?php foreach ($gosterilecek_veriler as $index => $kullanici): ?>
				<div class="accordion-item">
					<h2 class="accordion-header" id="heading-kullanici-<?php echo $kullanici['sira_no']; ?>">
						<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-kullanici-<?php echo $kullanici['sira_no']; ?>" aria-expanded="false" aria-controls="collapse-kullanici-<?php echo $kullanici['sira_no']; ?>">
							<?php echo $kullanici['sira_no'] . '. ' . htmlspecialchars($kullanici['adi']); ?>
							<span class="ms-2 badge bg-secondary"><?php echo htmlspecialchars($kullanici['id']); ?></span>
						</button>
					</h2>
					<div id="collapse-kullanici-<?php echo $kullanici['sira_no']; ?>" class="accordion-collapse collapse" aria-labelledby="heading-kullanici-<?php echo $kullanici['sira_no']; ?>">
						<div class="accordion-body">
							<?php if (empty($kullanici['oturumlar'])): ?>
								<p class="text-muted">Bu kullanıcı için oturum kaydı bulunamadı.</p>
							<?php else: ?>
								<table class="table table-sm table-striped table-hover">
									<thead><tr><th>E.T</th><th>Oturum Başlangıç</th><th>Oturum Bitiş</th><th>Oturum Süresi</th></tr></thead>
									<tbody>
										<?php 
										
											// Diziyi 'giris' alanına göre büyükten küçüğe (azalan) sırala
											usort($kullanici['oturumlar'], function($a, $b) {
												// Karşılaştırma fonksiyonu:
												// $b['giris'] değeri $a['giris'] değerinden büyükse pozitif sayı döner ($b öne gelir)
												// $b['giris'] değeri $a['giris'] değerinden küçükse negatif sayı döner ($a öne gelir)
												// Eğer eşitlerse 0 döner
												// Bu, büyükten küçüğe (azalan) sıralama sağlar.
												return $b['giris'] <=> $a['giris'];
											});
											
											foreach ($kullanici['oturumlar'] as $oturum): ?>
											<tr>
												<td><a href="http://istiklal.local/eta/monitor-cihaz-goster.php?mac=<?php echo urlencode($oturum['mac']); ?>" target="_blank"><?php echo htmlspecialchars(mac_den_gorunur_ad_getir($oturum['mac'], $envanter_arr)); ?></a></td>
												<td><?php echo $oturum['giris'] ? date('d.m.Y H:i:s', $oturum['giris']) : 'N/A'; ?></td>
												<td><?php echo $oturum['cikis'] ? date('d.m.Y H:i:s', $oturum['cikis']) : 'N/A'; ?></td>
												<td><?php echo ($oturum['sure'] !== null && $oturum['sure'] >= 0) ? format_sure($oturum['sure']) : (($oturum['cikis'] === null && $oturum['giris'] !== null) ? '-' : 'N/A'); ?></td>
											</tr>
										<?php endforeach; ?>
									</tbody>
								</table>
							<?php endif; ?>
						</div>
					</div>
				</div>
			<?php endforeach; ?>
		</div>
	<?php endif; ?>
</div>
