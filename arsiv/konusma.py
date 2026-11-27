"""Konuşma tanıma modeli (faster-whisper): GPU denetimi ve model yükleme."""
import ctypes
import os
import sys
from pathlib import Path

from .yollar import MODEL_KLASORU


def nvidia_dll_klasorlerini_ekle():
    """pip ile kurulan nvidia-cublas/cudnn paketlerinin DLL klasörlerini Windows arama yoluna ekler."""
    if os.name != 'nt':
        return
    for site in map(Path, sys.path):
        nvidia = site / 'nvidia'
        if nvidia.is_dir():
            for bin_klasoru in nvidia.glob('*/bin'):
                try:
                    os.add_dll_directory(str(bin_klasoru))
                except OSError:
                    pass
                os.environ['PATH'] = str(bin_klasoru) + os.pathsep + os.environ.get('PATH', '')


def gpu_durumu():
    """(kullanılabilir mi, açıklama). Model yüklemeden yalnızca donanım ve CUDA kütüphanesine bakar."""
    nvidia_dll_klasorlerini_ekle()
    try:
        import ctranslate2
        sayi = ctranslate2.get_cuda_device_count()
    except Exception as hata:
        return False, f'GPU kontrol edilemedi: {hata}'
    if not sayi:
        return False, 'NVIDIA GPU bulunamadı; CPU kullanılır.'
    if os.name == 'nt':
        try:
            # winmode=0: CTranslate2 gibi PATH'te de arar (ctypes varsayılanı aramaz).
            ctypes.WinDLL('cublas64_12.dll', winmode=0)
        except OSError:
            return False, 'NVIDIA GPU var ama CUDA 12 kütüphanesi (cublas64_12.dll) bulunamadı; CPU kullanılır.'
    return True, f'{sayi} NVIDIA GPU kullanıma hazır.'


def model_yukle(ad, birim, gunluk):
    """birim: 'auto', 'cuda' veya 'cpu'. GPU başlatılamazsa CPU'ya döner ve nedeni günlüğe yazılır."""
    import numpy as np
    from faster_whisper import WhisperModel
    klasor = str(MODEL_KLASORU)
    if birim != 'cpu':
        kullanilabilir, not_ = gpu_durumu()
        if kullanilabilir:
            try:
                model = WhisperModel(ad, device='cuda', compute_type='float16', download_root=klasor)
                # Eksik CUDA kütüphanesi hatası model yüklenirken değil, ilk çalıştırmada çıkar.
                list(model.transcribe(np.zeros(16000, dtype=np.float32), language='en', beam_size=1, vad_filter=False)[0])
                gunluk(f'İşlem birimi: GPU (NVIDIA CUDA). {not_}')
                return model
            except Exception as hata:
                gunluk(f'GPU başlatılamadı, CPU ile devam ediliyor: {hata}')
        else:
            gunluk(not_)
    gunluk('İşlem birimi: CPU.')
    return WhisperModel(ad, device='cpu', compute_type='int8', download_root=klasor)
