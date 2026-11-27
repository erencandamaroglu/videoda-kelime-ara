"""İngilizce arayüz metinleri: {Türkçe anahtar: İngilizce}. Süslü parantezli yer tutucular aynı kalmalıdır."""

INGILIZCE = {
    # Program
    'Videoda Kelime Ara': 'Video Word Search',
    'Uygulama zaten açık.': 'The application is already open.',

    # Süre / sayı biçimleri
    "1 dk'dan az": 'less than 1 min',
    '{gun} gün {sa} sa': '{gun} d {sa} h',
    '{sa} sa {dk} dk': '{sa} h {dk} min',
    '{dk} dk': '{dk} min',
    ' dk': ' min',
    '{sayi} bayt': '{sayi} bytes',

    # Ortak
    'Model:': 'Model:',
    'Dil:': 'Language:',
    'Model / dil:': 'Model / language:',
    'Türkçe': 'Turkish',
    'Otomatik algıla': 'Auto-detect',
    'İngilizce': 'English',
    'Klasör:': 'Folder:',
    'Süre:': 'Duration:',
    'Boyut:': 'Size:',
    'En az': 'Minimum',
    'En fazla': 'Maximum',
    '{ipucu} (sınırlar dahil). — : sınır yok': '{ipucu} (inclusive). — : no limit',
    'Alt sınır üst sınırdan büyük olamaz.': 'The lower limit cannot be greater than the upper limit.',
    'Tüm klasörler': 'All folders',
    'Tüm klasörlerde aranır': 'Searches all folders',
    '{yol}  ({sayi} video)': '{yol}  ({sayi} videos)',
    '{sayi} klasör: ': '{sayi} folders: ',
    'Detay': 'Details',
    'Videoyu aç': 'Open video',
    'Klasörünü aç': 'Open folder',
    'Seçili videonun SRT dosyasını kaydet': 'Save SRT of selected video',
    'SRT kaydet': 'Save SRT',
    'Altyazı (*.srt)': 'Subtitles (*.srt)',
    'Kapat': 'Close',
    'Yükleniyor…': 'Loading…',

    # Tablo sütunları
    'Video': 'Video',
    'Klasör': 'Folder',
    'Tür': 'Type',
    'Boyut': 'Size',
    'Süre': 'Duration',
    'İşlem': 'Job',
    'Durum': 'Status',
    'İlerleme': 'Progress',
    'Geçen süre': 'Elapsed',
    'Video / tam yol': 'Video / full path',
    'Çözünürlük': 'Resolution',
    'Satır': 'Lines',
    'Model / dil': 'Model / language',
    'MD5': 'MD5',
    'İlk eşleşme': 'First match',
    'Eşleşen satır': 'Matching lines',
    'Altyazı (ilk eşleşen satır)': 'Subtitle (first matching line)',
    'Görüntü': 'Preview',

    # İşçi aşamaları, iş türleri ve durumlar (anahtar olarak da kullanılır)
    'Klasörler taranıyor': 'Scanning folders',
    'Video süreleri okunuyor': 'Reading video durations',
    'Altyazı oluşturuluyor': 'Creating subtitles',
    'Video bilgileri okunuyor': 'Reading video info',
    'MD5 hesaplanıyor': 'Calculating MD5',
    'Altyazı': 'Subtitle',
    'Bekliyor': 'Waiting',
    'İşleniyor': 'Processing',
    'Tamamlandı': 'Completed',
    'Hata': 'Error',
    'Süre dışı': 'Out of range',
    'Durduruldu': 'Stopped',

    # Klasör tarama sekmesi
    'Klasör tarama': 'Folder scan',
    'Video klasörleri': 'Video folders',
    'Yalnızca işaretli klasörler taranır; alt klasörler de dahildir. Liste ve işaretler hatırlanır.':
        'Only checked folders are scanned, including subfolders. The list and checkmarks are remembered.',
    'Ekle': 'Add',
    'Çıkar': 'Remove',
    'Tümünü seç': 'Select all',
    'Hiçbirini seçme': 'Select none',
    'İşlenenleri yeniden oluştur': 'Recreate processed videos',
    'Eksik video bilgilerini ve MD5 değerlerini tamamla': 'Fill in missing video info and MD5 values',
    'Önceden işlenmiş videoların süre, tür, çözünürlük ve MD5 değerleri altyazı işinden sonra\n'
    'tamamlanır. MD5 için dosyanın tamamı okunur; büyük arşivde uzun sürebilir.\n'
    'Durdurulursa kalan videolar sonraki taramada devam eder.':
        'Duration, type, resolution and MD5 of previously processed videos are filled in after the subtitle job.\n'
        'MD5 reads the entire file; this can take a long time for a large archive.\n'
        'If stopped, the remaining videos continue in the next scan.',
    'Video süresi:': 'Video duration:',
    'Tüm süreler': 'All durations',
    'En fazla (≤)': 'At most (≤)',
    'En az (≥)': 'At least (≥)',
    'İki süre arasında': 'Between two durations',
    'Alt sınır:': 'Lower limit:',
    'Üst sınır:': 'Upper limit:',
    'Süre sınırları dahildir. Filtre dışındaki videolar işlenmez; mevcut kayıtlar korunur.':
        'Duration limits are inclusive. Videos outside the filter are not processed; existing records are kept.',
    'small: dengeli • base/tiny: daha hızlı • medium/large-v3: daha yavaş, daha fazla bellek\n'
    'İlk model indirmesi internet gerektirir. Sonraki işlemler yereldir. GPU / CPU seçimi Ayarlar sekmesindedir.':
        'small: balanced • base/tiny: faster • medium/large-v3: slower, more memory\n'
        'The first model download needs internet. Later processing is local. GPU / CPU choice is in the Settings tab.',
    'Tara ve altyazıları oluştur': 'Scan and create subtitles',
    'Durdur': 'Stop',
    'Hazır': 'Ready',
    'Liste': 'List',
    'Detaylı log': 'Detailed log',

    # Kelime arama sekmesi
    'Kelime arama / SRT': 'Word search / SRT',
    'Kelime yazın: hayat  •  Birden fazla kelime: birine mi muhtaç':
        'Type a word: life  •  Several words: do you need someone',
    'Ara': 'Search',
    'Listeyi yenile': 'Refresh list',
    'Yalnızca tam kelime': 'Whole words only',
    'Kapalıyken "hayat" araması "hayatı", "hayatımız" gibi ekli halleri de bulur.':
        'When off, searching "hayat" also finds suffixed forms such as "hayatı" and "hayatımız".',
    'Kapsam:': 'Scope:',
    'Aynı videoda (parçalı)': 'Same video (any lines)',
    'Aynı satırda': 'Same line',
    'Aynı videoda: her kelime ayrı aranır; hepsinin geçtiği videolardaki ilgili satırlar listelenir.\n'
    'Aynı satırda: tüm kelimeler aynı altyazı satırında olmalıdır.':
        'Same video: each word is searched separately; matching lines of videos containing all words are listed.\n'
        'Same line: all words must be in the same subtitle line.',
    'Görüntüleri göster': 'Show previews',
    'İlk eşleşme saniyesindeki kare arka planda üretilir ve veriler\\onizlemeler klasöründe saklanır.':
        'The frame at the first match is generated in the background and stored in the veriler\\onizlemeler folder.',
    '(isteğe bağlı; — sınır yok. Süresi henüz okunmamış videolar süre filtresinde listelenmez.)':
        '(optional; — no limit. Videos whose duration has not been read yet are not listed by the duration filter.)',
    'Büyük/küçük harf ve Türkçe karakter duyarsızdır: "dusunce" yazınca "Düşünce" de bulunur.':
        'Case and Turkish-character insensitive: typing "dusunce" also finds "Düşünce".',
    'Tüm altyazıları SRT olarak dışa aktar': 'Export all subtitles as SRT',
    'Detay (veya satıra çift tıklama): videonun tüm altyazısı ve oynatıcı açılır; video seçili satırın saniyesinden başlar.':
        'Details (or double-click a row): opens the full subtitle and a player; the video starts at the selected line.',
    '… {sayi} satır daha (Detay)': '… {sayi} more lines (Details)',
    ' İlk 1000 video gösteriliyor; aramanızı daraltın.': ' Showing the first 1000 videos; narrow your search.',
    '{videolar} video ({satirlar} eşleşen satır). Satırların tamamı için Detay.':
        '{videolar} videos ({satirlar} matching lines). Use Details to see all lines.',
    'Arama hatası': 'Search error',
    'Satır seçin': 'Select a row',
    'Önce listeden bir satır seçin.': 'Select a row in the list first.',
    'Detay açılamadı': 'Could not open details',
    'Video açılamadı': 'Could not open video',
    'Dosya yolunu ve varsayılan oynatıcınızı kontrol edin.': 'Check the file path and your default player.',
    'Video seçin': 'Select a video',
    'Önce listeden bir video seçin.': 'Select a video in the list first.',
    'SRT dosyalarının kaydedileceği klasör': 'Folder to save the SRT files',
    'Dışa aktarma': 'Export',
    'Dışa aktarma hatası': 'Export error',
    '{sayi} SRT dosyası kaydedildi.': '{sayi} SRT files saved.',

    # Video listesi sekmesi
    'Video listesi': 'Video list',
    'Ad / yol içerir (isteğe bağlı)': 'Name / path contains (optional)',
    'Uygula / yenile': 'Apply / refresh',
    'Sayfa başına:': 'Per page:',
    '◀ Önceki': '◀ Previous',
    'Sayfa': 'Page',
    'Sonraki ▶': 'Next ▶',
    'Seçilileri yeniden işle': 'Reprocess selected',
    'Filtreye uyan tüm videoları yeniden işle': 'Reprocess all videos matching the filter',
    'Kopuk bağları kontrol et': 'Check broken links',
    'Sütun başlığına tıklayarak sıralayın. Ctrl / Shift ile birden çok satır seçilir. Boş süre/MD5: bilgi henüz okunmadı '
    '(tarama sekmesinde "Eksik video bilgilerini ve MD5 değerlerini tamamla").':
        'Click a column header to sort. Use Ctrl / Shift to select several rows. Empty duration/MD5: not read yet '
        '(see "Fill in missing video info and MD5 values" in the scan tab).',
    '{toplam} video • {ilk}–{son} gösteriliyor': '{toplam} videos • showing {ilk}–{son}',
    'Tüm modeller': 'All models',
    '{model} / {dil}  ({sayi} video)': '{model} / {dil}  ({sayi} videos)',
    'Yeniden işle': 'Reprocess',
    '{sayi} videonun altyazısı seçilen modelle yeniden oluşturulacak.\n'
    'Eski altyazı, yenisi başarıyla kaydedilene kadar korunur.':
        'Subtitles of {sayi} videos will be recreated with the selected model.\n'
        'The old subtitle is kept until the new one is saved successfully.',
    'Devam eden işlem bitmeden yeni işlem başlatılamaz.': 'A new job cannot start before the current one finishes.',
    'İşlenecek video yok. Önce listeden video seçin veya filtreyi değiştirin.':
        'No videos to process. Select videos in the list or change the filter.',

    # Klasör listesi ve tarama başlatma
    'Video klasörü seçin': 'Select a video folder',
    'Klasör ekle': 'Add folder',
    'Bu klasör listede zaten var.': 'This folder is already in the list.',
    'Klasör listesi kaydedilemedi': 'Could not save the folder list',
    'veriler/ayarlar.ini dosyasına yazılamadı. Ağ bağlantısını ve yazma iznini kontrol edin.':
        'Could not write veriler/ayarlar.ini. Check the network connection and write permission.',
    'Klasör listesi': 'Folder list',
    'Süre filtresi': 'Duration filter',
    'Klasör kontrolü': 'Folder check',
    'Taranacak en az bir klasör işaretleyin.': 'Check at least one folder to scan.',
    'Bu klasörlere erişilemiyor:': 'These folders are not accessible:',
    'İşaretli klasörlerin hiçbirine erişilemiyor.': 'None of the checked folders are accessible.',
    'Otomatik tarama: klasörler taranıyor...': 'Automatic scan: scanning folders...',
    'Klasörler taranıyor...': 'Scanning folders...',

    # İlerleme
    '{ad}: işlenecek video yok': '{ad}: no videos to process',
    '{ad}: {yuzde}  ({biten} / {toplam} içerik)': '{ad}: {yuzde}  ({biten} / {toplam} of content)',
    '{ad}: {mevcut} / {toplam} video': '{ad}: {mevcut} / {toplam} videos',
    ' • Tahmini kalan: hesaplanıyor...': ' • Estimated remaining: calculating...',
    ' • Tahmini kalan: {kalan} • Tahmini bitiş: {bitis}': ' • Estimated remaining: {kalan} • Estimated finish: {bitis}',
    'Durduruluyor; devam eden model yükleme / ses çözümleme adımı bekleniyor...':
        'Stopping; waiting for the current model loading / audio decoding step...',
    'İşlem durduruluyor': 'Stopping the job',
    'İşlem durduktan sonra pencereyi kapatabilirsiniz. Tamamlanan videolar kaydedilmiştir.':
        'You can close the window after the job stops. Completed videos have been saved.',
    'Görüntü yok': 'No image',

    # Ayarlar ve zamanlayıcı
    'Ayarlar': 'Settings',
    'Arayüz dili:': 'Interface language:',
    'İşlem birimi:': 'Processing unit:',
    'Otomatik (GPU varsa GPU)': 'Automatic (GPU if available)',
    'GPU (NVIDIA CUDA)': 'GPU (NVIDIA CUDA)',
    'CPU': 'CPU',
    'GPU durumu:': 'GPU status:',
    'Ayarlar bir sonraki taramada geçerli olur. GPU başlatılamazsa işlem CPU ile sürer ve bu durum Detaylı log sekmesine yazılır.':
        'Settings take effect in the next scan. If the GPU cannot start, processing continues on the CPU and this is '
        'written to the Detailed log tab.',
    'Otomatik tarama zamanlayıcısı': 'Automatic scan scheduler',
    'Belirlenen saatlerde otomatik tara': 'Scan automatically at set times',
    'Başlangıç:': 'Start:',
    'Bitiş:': 'End:',
    'Başlangıç saatinde, Klasör tarama sekmesindeki işaretli klasörler ve ayarlarla (model, dil, süre filtresi, '
    'eksik bilgileri tamamla) tarama başlar. "İşlenenleri yeniden oluştur" otomatik taramada kullanılmaz.\n'
    'Bitiş saatinde işlenmekte olan video tamamlanır, sıradaki videolar bir sonraki aralığa kalır. '
    'Bitiş başlangıçtan küçükse aralık gece yarısını aşar (ör. 20:00 – 07:00).\n'
    'Her aralıkta bir kez çalışır. Uygulamanın açık kalması gerekir; tarama sürerken bilgisayarın '
    'uykuya geçmesi engellenir.':
        'At the start time, a scan begins with the checked folders and settings of the Folder scan tab (model, language, '
        'duration filter, fill in missing info). "Recreate processed videos" is not used in automatic scans.\n'
        'At the end time, the video being processed is finished and the remaining videos wait for the next window. '
        'If the end is earlier than the start, the window passes midnight (e.g. 20:00 – 07:00).\n'
        'Runs once per window. The application must stay open; the computer is kept from sleeping during the scan.',
    'Otomatik tarama sürüyor; {bitis} itibarıyla işlenmekte olan video bitince durdurulacak.':
        'Automatic scan running; from {bitis} it will stop after the current video finishes.',
    '[{saat}] Zamanlayıcı: bitiş saati geldi; işlenmekte olan video tamamlanıp durdurulacak.':
        '[{saat}] Scheduler: end time reached; the current video will be finished, then the scan stops.',
    'Zamanlayıcı bitiş saati: işlenmekte olan video tamamlanıp durdurulacak...':
        'Scheduler end time: the current video will be finished, then the scan stops...',
    'Zamanlayıcı kapalı.': 'Scheduler is off.',
    'Başlangıç ve bitiş saati aynı olamaz.': 'Start and end time cannot be the same.',
    'Otomatik tarama zamanı geldi; devam eden işlem bitince başlayacak.':
        'Automatic scan time has come; it will start when the current job finishes.',
    '[{saat}] Zamanlayıcı: otomatik tarama başlatılıyor.': '[{saat}] Scheduler: starting automatic scan.',
    'Sonraki otomatik tarama: {bas} – {bit}': 'Next automatic scan: {bas} – {bit}',
    '[{saat}] Zamanlayıcı: otomatik tarama sona erdi. {durum}': '[{saat}] Scheduler: automatic scan finished. {durum}',
    'Zamanlayıcı — {baslik}: {metin}': 'Scheduler — {baslik}: {metin}',
    'Otomatik tarama başlatılamadı: {metin}': 'Automatic scan could not start: {metin}',
    'Zamanlayıcı — erişilemeyen klasörler atlandı:': 'Scheduler — inaccessible folders skipped:',

    # GPU / model
    'GPU kontrol edilemedi: {hata}': 'Could not check the GPU: {hata}',
    'NVIDIA GPU bulunamadı; CPU kullanılır.': 'No NVIDIA GPU found; the CPU is used.',
    'NVIDIA GPU var ama CUDA 12 kütüphanesi (cublas64_12.dll) bulunamadı; CPU kullanılır.':
        'An NVIDIA GPU is present but the CUDA 12 library (cublas64_12.dll) was not found; the CPU is used.',
    '{sayi} NVIDIA GPU kullanıma hazır.': '{sayi} NVIDIA GPU(s) ready.',
    'İşlem birimi: GPU (NVIDIA CUDA). {not_}': 'Processing unit: GPU (NVIDIA CUDA). {not_}',
    'GPU başlatılamadı, CPU ile devam ediliyor: {hata}': 'Could not start the GPU, continuing on the CPU: {hata}',
    'İşlem birimi: CPU.': 'Processing unit: CPU.',

    # Süre filtresi
    'En fazla {dk} dakika': 'At most {dk} minutes',
    'En az {dk} dakika': 'At least {dk} minutes',
    '{alt}–{ust} dakika arasında (sınırlar dahil)': 'Between {alt}–{ust} minutes (inclusive)',
    'Geçersiz süre filtresi.': 'Invalid duration filter.',
    'Süreler sıfır veya pozitif olmalı.': 'Durations must be zero or positive.',
    'Alt süre sınırı üst sınırdan büyük olamaz.': 'The lower duration limit cannot be greater than the upper limit.',
    'Video süresi okunamadı.': 'Could not read the video duration.',
    'Video süresi okunamadı; süre filtresi açık olduğu için işlenmedi.':
        'Could not read the video duration; not processed because the duration filter is on.',

    # Tarama işçisi günlüğü ve sonuç
    '{sayi} video yeniden işlenecek.': '{sayi} videos will be reprocessed.',
    'Klasör bulunamadı: {kok}': 'Folder not found: {kok}',
    'Tarama durduruldu.': 'Scan stopped.',
    '{bulunan} video bulundu: {atlanan} önceden işlenmiş, {bekleyen} işlenecek.':
        '{bulunan} videos found: {atlanan} already processed, {bekleyen} to process.',
    'Süre filtresi: {aciklama}': 'Duration filter: {aciklama}',
    '{onek}: {islenen} işlendi, {atlanan} önceden işlenmiş, {sure_disi} süre dışı, {hatali} hata':
        '{onek}: {islenen} processed, {atlanan} already processed, {sure_disi} out of duration range, {hatali} errors',
    ', {sayi} bağ düzeltildi': ', {sayi} links fixed',
    ', {sayi} kopuk kayıt (Video listesi > Kopuk bağları kontrol et)': ', {sayi} broken records (Video list > Check broken links)',
    ', {sayi} videonun bilgisi tamamlandı': ', info completed for {sayi} videos',
    ', {sayi} bilgi okunamadı': ', {sayi} could not be read',
    'İşlem başarısız: {hata}': 'Job failed: {hata}',
    'Bağ düzeltildi: {eski} -> {yeni}': 'Link fixed: {eski} -> {yeni}',
    'Kopuk kayıt (dosya bulunamadı): {yol}': 'Broken record (file not found): {yol}',
    'Video bilgileri okunamadı: {ad} ({hata})': 'Could not read video info: {ad} ({hata})',
    'Süre nedeniyle atlandı: {ad} ({dk} dk)': 'Skipped due to duration: {ad} ({dk} min)',
    'Konuşma modeli yükleniyor; ilk kullanımda internetten indirilir...':
        'Loading the speech model; it is downloaded from the internet on first use...',
    '[{i}/{toplam}] İşleniyor: {dosya}': '[{i}/{toplam}] Processing: {dosya}',
    '  {ad}: {sn} / {toplam} saniye': '  {ad}: {sn} / {toplam} seconds',
    'Video işlem sırasında değişti; yeniden tarayın.': 'The video changed during processing; scan again.',
    'Kaydedildi: {ad} ({sayi} altyazı satırı)': 'Saved: {ad} ({sayi} subtitle lines)',
    'HATA — {dosya}: {hata}': 'ERROR — {dosya}: {hata}',
    '{ad}: {sayi} video.': '{ad}: {sayi} videos.',
    'Video değişmiş; bir sonraki taramada yeniden işlenecek.': 'The video has changed; it will be reprocessed in the next scan.',
    'Bilgi okunamadı — {yol}: {hata}': 'Could not read info — {yol}: {hata}',
    '{sayi} kopuk kayıt bulundu; yeni yerleri aranıyor (klasör taraması birkaç dakika sürebilir)...':
        '{sayi} broken records found; searching for their new locations (the folder scan may take a few minutes)...',
    '{sayi} kaydın dosyası kontrol ediliyor...': 'Checking the files of {sayi} records...',
    'MD5 aynı': 'Same MD5',
    'Boyut ve tarih aynı': 'Same size and date',
    '{sayi} kopya var; biri seçildi': '{sayi} copies; one was chosen',
    'Yalnızca boyut aynı': 'Same size only',
    'Yalnızca ad aynı': 'Same name only',

    # Kopuk bağlar penceresi
    'Kopuk bağlar': 'Broken links',
    'Kayıtlı yol': 'Recorded path',
    'Önerilen yeni yol': 'Suggested new path',
    'Neden': 'Reason',
    'Önerileri uygula': 'Apply suggestions',
    'Dosyayı elle seç…': 'Choose file manually…',
    'Başka klasörde ara…': 'Search another folder…',
    'Kayıttan kaldır': 'Remove from records',
    'Ctrl / Shift ile birden çok satır, Ctrl+A ile tümü seçilir. Yeşil öneriler kesin eşleşmedir; '
    'kaldırmak altyazıyı da siler, video dosyasına dokunmaz.':
        'Use Ctrl / Shift for several rows, Ctrl+A for all. Green suggestions are certain matches; '
        'removing also deletes the subtitle but never touches the video file.',
    '{sayi} kopuk kayıt, {onerili} tanesi için öneri var.': '{sayi} broken records, suggestions for {onerili}.',
    'Kopuk kayıt yok; tüm kayıtların dosyası yerinde.': 'No broken records; all recorded files are in place.',
    'Önerisi olan satırları seçin.': 'Select rows that have a suggestion.',
    '{sayi} önerinin {kesin_olmayan} tanesi kesin değil; altyazı başka bir videoya bağlanabilir. Uygulansın mı?':
        '{kesin_olmayan} of {sayi} suggestions are not certain; a subtitle may be linked to a different video. Apply?',
    'bu dosyanın zaten ayrı bir kaydı var.': 'this file already has its own record.',
    '{sayi} bağ düzeltildi. Düzeltilemeyenler:': '{sayi} links fixed. Could not fix:',
    'Dosyayı elle seç': 'Choose file manually',
    'Tek bir satır seçin.': 'Select a single row.',
    'Videonun yeni yeri': 'New location of the video',
    'Seçilen dosyanın boyutu kayıttakinden farklı; farklı bir video olabilir. Altyazı yine de buna bağlansın mı?':
        'The selected file has a different size than recorded; it may be a different video. Link the subtitle anyway?',
    'Bu dosyanın zaten ayrı bir kaydı var. Eski kaydı isterseniz kaldırabilirsiniz.':
        'This file already has its own record. You can remove the old record if you want.',
    'Kopuk videoların aranacağı klasör': 'Folder to search for broken videos',
    'Önce satır seçin.': 'Select rows first.',
    '{sayi} videonun kaydı ve altyazısı veritabanından silinecek. Bu işlem geri alınamaz. Devam edilsin mi?':
        'The records and subtitles of {sayi} videos will be deleted from the database. This cannot be undone. Continue?',

    # Detay penceresi
    'Detay • {ad}': 'Details • {ad}',
    'Oynat': 'Play',
    'Duraklat': 'Pause',
    'Başlangıç': 'Start',
    'Bitiş': 'End',
    'Oynatırken altyazıyı takip et': 'Follow subtitle while playing',
    '{sayi} satır': '{sayi} lines',
    ' • {sayi} satırda aranan kelime var (sarı)': ' • {sayi} lines contain the searched words (yellow)',
    ' • Satıra tıklayın: video o saniyeden oynar.': ' • Click a line: the video plays from that second.',
    "VLC'de bu saniyeden aç": 'Open in VLC at this second',
    'VLC bulunamadı. https://www.videolan.org adresinden kurulabilir.': 'VLC not found. It can be installed from https://www.videolan.org.',
    'Varsayılan oynatıcıda aç': 'Open in default player',
    'Metni kopyala': 'Copy text',
    'Video burada oynatılamadı: {mesaj}\nVLC veya varsayılan oynatıcı düğmesini kullanın.':
        'The video cannot be played here: {mesaj}\nUse the VLC or default player button.',
    'VLC açılamadı': 'Could not open VLC',
}
