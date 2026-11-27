"""Taramada video süresine göre filtre (dakika cinsinden sınırlar, sınırlar dahil)."""
import math
from dataclasses import dataclass

from .ceviri import _t

MODLAR = ('tumu', 'en_fazla', 'en_az', 'arasinda')
# ayarlar.ini'de eski sürümün yazdığı değerler
ESKI_MODLAR = {'all': 'tumu', 'maximum': 'en_fazla', 'minimum': 'en_az', 'between': 'arasinda'}


@dataclass(frozen=True)
class SureFiltresi:
    mod: str = 'tumu'
    en_az: float = 0
    en_fazla: float = 10

    def __post_init__(self):
        if self.mod not in MODLAR:
            raise ValueError(_t('Geçersiz süre filtresi.'))
        if not all(math.isfinite(d) and d >= 0 for d in (self.en_az, self.en_fazla)):
            raise ValueError(_t('Süreler sıfır veya pozitif olmalı.'))
        if self.mod == 'arasinda' and self.en_az > self.en_fazla:
            raise ValueError(_t('Alt süre sınırı üst sınırdan büyük olamaz.'))

    def kabul_eder(self, saniye):
        if self.mod == 'tumu':
            return True
        if not math.isfinite(saniye) or saniye < 0:
            raise ValueError(_t('Video süresi okunamadı.'))
        return ((self.mod not in ('en_az', 'arasinda') or saniye >= self.en_az * 60)
                and (self.mod not in ('en_fazla', 'arasinda') or saniye <= self.en_fazla * 60))

    def aciklama(self):
        if self.mod == 'en_fazla':
            return _t('En fazla {dk} dakika', dk=f'{self.en_fazla:g}')
        if self.mod == 'en_az':
            return _t('En az {dk} dakika', dk=f'{self.en_az:g}')
        if self.mod == 'arasinda':
            return _t('{alt}–{ust} dakika arasında (sınırlar dahil)', alt=f'{self.en_az:g}', ust=f'{self.en_fazla:g}')
        return _t('Tüm süreler')


def video_suresi(yol):
    """Videoyu veya sesini çözmeden yalnızca başlık bilgisinden süreyi okur."""
    from .medya_bilgisi import incele
    sure = incele(yol)['duration']
    if sure is None:
        raise ValueError(_t('Video süresi okunamadı; süre filtresi açık olduğu için işlenmedi.'))
    return sure
