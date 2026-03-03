

<script>
    document.addEventListener("DOMContentLoaded", function () {
        let zamanlayici;
        let kalanSure = 60;
        const sayacElement = document.getElementById('sayac');

        function sayaciBaslat() {
            clearInterval(zamanlayici);
            kalanSure = 60;
            sayacElement.textContent = kalanSure;

            zamanlayici = setInterval(() => {
                kalanSure--;
                sayacElement.textContent = kalanSure;
                if (kalanSure <= 0) {
                    clearInterval(zamanlayici);
                    location.reload();
                }
            }, 1000);
        }

        // Kullanıcı etkileşimini dinle
        ['click', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(function(evt) {
            window.addEventListener(evt, sayaciBaslat, true);
        });

        // İlk başlatma
        sayaciBaslat();
    });
</script>

<div id="sayacKutusu" style="
    position: fixed;
    bottom: 10px;
    right: 10px;
    background: #f8f9fa;
    border: 1px solid #ced4da;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 0.9rem;
    color: #333;
    box-shadow: 0 0 5px rgba(0,0,0,0.2);
    z-index: 9999;
">
    Yenilemeye: <span id="sayac">60</span> sn
</div>