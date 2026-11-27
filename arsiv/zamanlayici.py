"""Otomatik tarama zamanlayıcısının saat hesapları (arayüzden bağımsız, test edilebilir)."""
import os
from datetime import datetime, time, timedelta


def etkin_aralik(simdi, baslangic, bitis):
    """simdi, [baslangic, bitis) aralığındaysa o aralığın başladığı anı (datetime), değilse None döndürür.
    baslangic > bitis ise aralık gece yarısını aşar (ör. 20:00–07:00). baslangic == bitis geçersizdir."""
    if baslangic == bitis:
        return None
    bugun = simdi.date()
    if baslangic < bitis:
        return datetime.combine(bugun, baslangic) if baslangic <= simdi.time() < bitis else None
    if simdi.time() >= baslangic:
        return datetime.combine(bugun, baslangic)
    if simdi.time() < bitis:
        return datetime.combine(bugun - timedelta(days=1), baslangic)
    return None


def aralik_sonu(aralik_basi, baslangic, bitis):
    """Aralığın bitiş anı."""
    gun = aralik_basi.date() + timedelta(days=1 if baslangic > bitis else 0)
    return datetime.combine(gun, bitis)


def sonraki_baslangic(simdi, baslangic, bitis):
    """Bir sonraki aralığın başlama anı (simdi aralık içindeyse bir sonraki günün)."""
    aday = datetime.combine(simdi.date(), baslangic)
    if aday <= simdi:
        aday += timedelta(days=1)
    return aday


def saat_coz(metin, varsayilan):
    """'SS:DD' metnini time nesnesine çevirir; bozuksa varsayilan döner."""
    try:
        saat, dakika = (int(parca) for parca in metin.split(':'))
        return time(saat, dakika)
    except (ValueError, AttributeError):
        return varsayilan


def uyanik_tut(acik):
    """Windows'un tarama sürerken uyku moduna geçmesini engeller (ekranın kapanmasına izin verir).
    Ana iş parçacığından çağrılmalıdır."""
    if os.name != 'nt':
        return
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if acik else 0))
