<?php

include(__DIR__ . '/lib.php');
error_reporting(0);


// İşlem kontrolü
if (!isset($_GET['islem']))
    exit();

if ($_GET['islem'] === 'hostnamegetir') {
	
	// http://istiklal.local/eta/index.php?islem=hostnamegetir
    $ip = $_SERVER['REMOTE_ADDR'];
    $mac = empty($_GET['mac']) ? 'nomac' : $_GET['mac'];
    $ret['host-name'] = envanterden_hostname_uret(envanter_getir($mac));
    echo json_encode($ret);
    exit();
}


if ($_GET['islem'] === 'benkimim') {

    //http://istiklal.local/eta/index.php?islem=benkimim&mac=00:09:df:8a:b8:fb

    $ip = $_SERVER['REMOTE_ADDR'];
    $mac = empty($_GET['mac']) ? 'nomac' : $_GET['mac'];
    echo envanterden_hostname_uret(envanter_getir($mac));
    exit();
}


if ($_GET['islem'] === 'log') {

    // Ana log dosyasına logla
    $ip = $_SERVER['REMOTE_ADDR'];
    $log = str_replace('\/', '/', urldecode($_GET['log']));
    $mac = empty($_GET['mac']) ? 'nomac' : $_GET['mac'];
    $data = [
        's' => $_GET['seviye'],
        'l' => $log,
        'i' => $ip,
        'm' => $mac,
        'z' => time()
    ];
    $existingData = json_decode(file_get_contents(__DIR__ . '/logs.json'), true);
    $existingData[] = $data;
    file_put_contents(__DIR__ . '/logs.json', json_encode($existingData, JSON_PRETTY_PRINT));

    // ----------------------------------------------------------
    // Kullanıcıları ve parolalarını (EBA ID) logla
    // Örnek string: "Login FIFO'suna (/var/lib/lightdm/pardus-greeter) JSON olarak ozgur-koca-qr,2d383786bccd0ee65c1683e8d1fd0062,None yazildi.";
    // ----------------------------------------------------------
    $alanlar = explode(',', aradakini_getir($log, 'JSON olarak', 'yazildi.'));
    $kullanici = trim($alanlar[0]);
    $eba_id = trim($alanlar[1]);

    if (!empty($kullanici) and !empty($eba_id)) {
        $kullanicilar = json_decode(file_get_contents(__DIR__ . '/kullanicilar.json'), true);
        $kullanicilar[$kullanici] = $eba_id;
        file_put_contents(__DIR__ . '/kullanicilar.json', json_encode($kullanicilar, JSON_PRETTY_PRINT));
    }

    // ----------------------------------------------------------
    // Oturum açma ve kapanma zamanlarını logla
    // ----------------------------------------------------------
    // "ozgur-koca-qr oturumu kapaniyor (\/usr\/share\/lighdm\/lightdm.conf.d\/90-kapanis-logla.conf)"
    $ko_patika = __DIR__ . '/kullanicilarin-oturum-zamanlari.json';

    if (strpos($log, ' oturumu kapaniyor ') !== false) {
        $kullanici = trim(explode(' ', trim($log))[0]);
        $oturumlar = json_decode(file_get_contents($ko_patika), true);
        $oturumlar[$kullanici]['k'][$mac][] = time();
        file_put_contents($ko_patika, json_encode($oturumlar, JSON_PRETTY_PRINT));
    }

    // "ozgur-koca-qr:1332ec317bcf1a1c540ce92c73818383 oturum acti (cli.py)."
    if (strpos($log, 'oturum acti (cli.py)') !== false) {
		
        $kullanici_ve_id = explode(' ', trim($log))[0];
        $kullanici = explode(':', trim($kullanici_ve_id))[0];
        $eba_id = explode(':', trim($kullanici_ve_id))[1];
        $oturumlar = json_decode(file_get_contents($ko_patika), true);
        $oturumlar[$kullanici]['a'][$mac][] = time();
        file_put_contents($ko_patika, json_encode($oturumlar, JSON_PRETTY_PRINT));

        $kid_patika = __DIR__ . '/kullanicilarin-idleri.json';
        $kullanicilar = json_decode(file_get_contents($kid_patika), true);
        $kullanicilar[$kullanici]=$eba_id;
        file_put_contents($kid_patika, json_encode($kullanicilar, JSON_PRETTY_PRINT));
    }

    // ----------------------------------------------------------
    // Tahta açılış kapanış zamanlarını logla
    // ----------------------------------------------------------
    // Açılış sırasında ağ oturmadığı için burayı yakalayamıyorum
    // "Tahta aciliyor (acilis-kapanis-logla.service)."
    if (strpos($log, 'Tahta aciliyor ') !== false) {
        $tahtalar = json_decode(file_get_contents(__DIR__ . '/tahta-acilis-kapanis.json'), true);
        $tahtalar[$mac]['a'][] = time();
        file_put_contents(__DIR__ . '/tahta-acilis-kapanis.json', json_encode($tahtalar, JSON_PRETTY_PRINT));
    }

    // Tahta kapanışı çok hızlı olduğu için burayı yakalayamıyorum
    // "Tahta kapaniyor (\/etc\/systemd\/system\/tahta-kapanis-logla.service)"
    if (strpos($log, 'Tahta kapaniyor ') !== false) {
        $tahtalar = json_decode(file_get_contents(__DIR__ . '/tahta-acilis-kapanis.json'), true);
        $tahtalar[$mac]['k'][] = time();
        file_put_contents(__DIR__ . '/tahta-acilis-kapanis.json', json_encode($tahtalar, JSON_PRETTY_PRINT));
    }
}

?>
