<?php
error_reporting(E_ALL ^E_WARNING ^E_NOTICE ^E_DEPRECATED);
session_start();

// Etkileşimli tahta üzerindeki sudo yetkilisi
$ET_USERNAME = 'etapadmin';
$ET_PASSWORD = '1m0crazy';

// eth0: İdare Ağı
$IDARE_AG_ARALIGI = "192.168.16.0/21";

// eth1: ET Ağı
$ET_AG_ARALIGI = "10.255.187.0/24";

// Monitör arayüzünün parolası
$MASTER_PASSWORD = 'wdysay';
?>

