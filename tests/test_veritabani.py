import sqlite3
import tempfile
import unittest
from pathlib import Path

from arsiv.veritabani import (altyaziyi_kaydet, ara, baglan, kokleri_ekle, kokleri_listele, modelleri_listele, srt_aktar,
                              video_yollari, videolari_listele, zaman_damgasi)


class VeritabaniTestleri(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self.gecici.name)
        self.db = baglan(self.kok / 'test.sqlite3')
        self.video = self.kok / 'örnek.mp4'
        self.video.write_bytes(b'test')

    def tearDown(self):
        self.db.close()
        self.gecici.cleanup()

    def kaydet(self, satirlar):
        altyaziyi_kaydet(self.db, self.video, self.video.stat(), 'small', 'tr', satirlar)

    def test_turkce_arama_ve_ozel_karakterli_sorgu(self):
        self.kaydet([(0, 1, 'İSTANBUL ışık hayat'), (1, 2, 'Hayat güzeldir')])
        self.assertEqual(len(ara(self.db, 'istanbul IŞIK')), 1)
        self.assertEqual(len(ara(self.db, 'HAYAT')), 2)
        self.assertEqual(len(ara(self.db, 'hay')), 2)
        self.assertEqual(len(ara(self.db, 'hay', tam_kelime=True)), 0)
        self.assertEqual(len(ara(self.db, '" OR hayat')), 0)
        self.assertEqual(ara(self.db, '"'), [])

    def test_turkce_karakterler_sadelesir(self):
        self.kaydet([(0, 1, 'Kim ne DÜŞÜNÜRSE düşünsün'), (1, 2, "İstanbul'da IŞIKLAR yandı"), (2, 3, 'Çocuğun ağacı')])
        for sorgu in ['dusunurse', 'DÜŞÜNÜRSE', 'düşünürse', 'istanbul', 'ISTANBUL', 'ıstanbul', 'isik', 'IŞIK', 'ışıklar',
                      'cocugun', 'AGACI']:
            self.assertEqual(len(ara(self.db, sorgu)), 1, sorgu)
        self.assertEqual(len(ara(self.db, 'isik', tam_kelime=True)), 0)
        self.assertEqual(len(ara(self.db, 'isiklar', tam_kelime=True)), 1)

    def test_video_kapsami_kelimeleri_satirlar_arasinda_eslestirir(self):
        self.kaydet([(0, 1, 'Birine'), (1, 2, 'mi kaldın'), (2, 3, 'MUHTAÇ değilsin'), (3, 4, 'alakasız satır')])
        diger = self.kok / 'diger.mp4'
        diger.write_bytes(b'y')
        altyaziyi_kaydet(self.db, diger, diger.stat(), 'small', 'tr', [(0, 1, 'birine muhtac')])
        self.assertEqual(len(ara(self.db, 'birine mi muhtaç')), 0)
        satirlar = ara(self.db, 'birine mi muhtaç', kapsam='video')
        self.assertEqual([s['text'] for s in satirlar], ['Birine', 'mi kaldın', 'MUHTAÇ değilsin'])
        self.assertEqual(len(ara(self.db, 'birine muhtac', kapsam='video')), 3)
        self.assertEqual(len(ara(self.db, 'birine muhtac', kapsam='video', kokler=[self.video])), 0)

    def test_klasor_filtresi(self):
        diger = self.kok / 'Başka Klasör' / 'video.mp4'
        diger.parent.mkdir()
        diger.write_bytes(b'x')
        self.kaydet([(0, 1, 'ortak kelime')])
        altyaziyi_kaydet(self.db, diger, diger.stat(), 'small', 'tr', [(0, 1, 'ortak kelime')])
        kokleri_ekle(self.db, [self.kok, diger.parent])
        self.assertEqual(len(ara(self.db, 'ortak')), 2)
        self.assertEqual(len(ara(self.db, 'ortak', kokler=[diger.parent])), 1)
        self.assertEqual(len(ara(self.db, 'ortak', kokler=[str(diger.parent).upper()])), 1)
        self.assertEqual(len(ara(self.db, 'ortak', kokler=[self.kok / 'Başka'])), 0)
        self.assertEqual(len(ara(self.db, 'ortak', kokler=[self.kok / 'Başka', diger.parent])), 1)
        self.assertEqual(len(ara(self.db, 'ortak', kokler=[self.kok, diger.parent])), 2)
        kokler = dict(kokleri_listele(self.db, [self.kok / 'boş']))
        self.assertEqual(kokler, {str(self.kok): 2, str(diger.parent): 1})

    def test_eski_dizin_yeniden_kurulur(self):
        self.kaydet([(0, 1, 'Düşünce')])
        self.db.execute("UPDATE search_index SET text='eski'")
        self.db.execute('PRAGMA user_version=0')
        self.db.commit()
        self.db.close()
        self.db = baglan(self.kok / 'test.sqlite3')
        self.assertEqual(len(ara(self.db, 'dusunce')), 1)
        self.assertEqual(len(ara(self.db, 'eski')), 0)

    def test_yeni_altyazi_eski_dizini_siler(self):
        self.kaydet([(0, 1, 'eski kelime')])
        self.kaydet([(2, 3, 'yeni cümle')])
        self.assertEqual(len(ara(self.db, 'eski')), 0)
        self.assertEqual(len(ara(self.db, 'yeni')), 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM videos').fetchone()[0], 1)

    def test_basarisiz_guncelleme_onceki_altyaziyi_korur(self):
        self.kaydet([(0, 1, 'önceki metin')])
        with self.assertRaises(Exception):
            self.kaydet([(0, 1, None)])
        self.assertEqual(len(ara(self.db, 'önceki')), 1)

    def test_srt(self):
        hedef = self.kok / 'altyazı.srt'
        srt_aktar([(1.125, 62.5, 'Türkçe metin')], hedef)
        self.assertIn('00:00:01,125 --> 00:01:02,500', hedef.read_text(encoding='utf-8-sig'))
        self.assertEqual(zaman_damgasi(3599.9999), '01:00:00,000')


class ListeTestleri(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self.gecici.name)
        self.db = baglan(self.kok / 'test.sqlite3')
        for i, (sure, boyut) in enumerate([(30, 10), (300, 2000), (900, 500)]):
            video = self.kok / f'video{i}.mp4'
            video.write_bytes(b'x' * boyut)
            altyaziyi_kaydet(self.db, video, video.stat(), 'small', 'tr', [(0, 1, 'ortak kelime')],
                             {'duration': sure, 'width': 640, 'height': 360})
        self.db.execute("UPDATE videos SET duration=NULL WHERE path LIKE '%video0.mp4'")

    def tearDown(self):
        self.db.close()
        self.gecici.cleanup()

    def test_sayfalama_siralama_ve_filtreler(self):
        toplam, satirlar = videolari_listele(self.db, sinir=2)
        self.assertEqual((toplam, [Path(s['path']).name for s in satirlar]), (3, ['video0.mp4', 'video1.mp4']))
        toplam, satirlar = videolari_listele(self.db, sinir=2, atla=2)
        self.assertEqual([Path(s['path']).name for s in satirlar], ['video2.mp4'])
        _, satirlar = videolari_listele(self.db, sira='boyut', azalan=True)
        self.assertEqual([s['size'] for s in satirlar], [2000, 500, 10])
        self.assertEqual(videolari_listele(self.db, sure=(60, None))[0], 2)
        self.assertEqual(videolari_listele(self.db, sure=(60, 600))[0], 1)
        self.assertEqual(videolari_listele(self.db, boyut=(None, 600))[0], 2)
        self.assertEqual(videolari_listele(self.db, ad='VİDEO2')[0], 1)
        self.assertEqual(videolari_listele(self.db)[1][0]['satir'], 1)

    def test_model_filtresi_ve_tum_yollar(self):
        self.db.execute("UPDATE videos SET model='large-v3' WHERE path LIKE '%video2.mp4'")
        self.assertEqual(modelleri_listele(self.db), [('small', 'tr', 2), ('large-v3', 'tr', 1)])
        self.assertEqual(videolari_listele(self.db, model=('small', 'tr'))[0], 2)
        self.assertEqual(videolari_listele(self.db, model=('large-v3', 'en'))[0], 0)
        yollar = video_yollari(self.db, model=('large-v3', 'tr'))
        self.assertEqual([Path(y).name for y in yollar], ['video2.mp4'])
        self.assertEqual(len(video_yollari(self.db, boyut=(100, None), model=('small', 'tr'))), 1)

    def test_arama_filtreleri(self):
        self.assertEqual(len(ara(self.db, 'ortak')), 3)
        self.assertEqual(len(ara(self.db, 'ortak', sure=(None, 600))), 1)
        self.assertEqual(len(ara(self.db, 'ortak', kapsam='video', boyut=(100, None))), 2)

    def test_eski_veritabanina_yeni_sutunlar_eklenir(self):
        yol = self.kok / 'eski.sqlite3'
        eski = sqlite3.connect(yol)
        eski.execute('CREATE TABLE videos (id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, size INTEGER NOT NULL, '
                     'mtime INTEGER NOT NULL, status TEXT NOT NULL, error TEXT, model TEXT, language TEXT)')
        eski.execute(r"INSERT INTO videos(path,size,mtime,status) VALUES('C:\a\film.Mov',1,1,'done')")
        eski.commit()
        eski.close()
        db = baglan(yol)
        satir = db.execute('SELECT format,md5,duration FROM videos').fetchone()
        self.assertEqual(tuple(satir), ('MOV', None, None))
        db.close()


if __name__ == '__main__':
    unittest.main()
