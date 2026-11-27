"""Video başlık bilgileri (süre, codec, çözünürlük) ve MD5."""
import hashlib
import math

PARCA = 8 * 1024 * 1024


def kap_suresi(kap):
    import av
    sureler = [float(a.duration * a.time_base) for a in kap.streams.video
               if a.duration is not None and a.time_base is not None]
    sureler = [s for s in sureler if math.isfinite(s) and s > 0]
    if sureler:
        return max(sureler)
    if kap.duration is not None:
        sure = float(kap.duration / av.time_base)
        if math.isfinite(sure) and sure > 0:
            return sure
    return None


def incele(yol):
    """Süre, codec ve çözünürlüğü video başlığından okur; video veya ses çözülmez.
    Anahtarlar veritabanı sütun adlarıdır (duration, codec, width, height)."""
    import av
    with av.open(str(yol)) as kap:
        video = kap.streams.video[0] if kap.streams.video else None
        return {'duration': kap_suresi(kap),
                'codec': video.codec_context.name if video else None,
                'width': (video.width or None) if video else None,
                'height': (video.height or None) if video else None}


def dosya_md5(yol, durdu=lambda: False, ilerleme=None):
    """Dosyanın MD5 değeri; durdu() True dönerse None döndürür. ilerleme(okunan bayt) isteğe bağlıdır."""
    ozet = hashlib.md5()
    okunan = 0
    with open(yol, 'rb') as dosya:
        while parca := dosya.read(PARCA):
            if durdu():
                return None
            ozet.update(parca)
            okunan += len(parca)
            if ilerleme:
                ilerleme(okunan)
    return ozet.hexdigest()
