# Video Word Search

[Türkçe](README.md) | English

Creates subtitles from the speech in your video folders (faster-whisper), stores them in SQLite and lets you search words across the whole archive. The interface is available in Turkish and English (Settings → Interface language).

## Installation and running (Windows)

- **First install:** `kurulum.bat` — creates the Python virtual environment in `.venv` inside the project folder; if an NVIDIA card is present it also installs the GPU libraries (`requirements-gpu.txt`).
- **Start:** `baslat.bat` (`.venv\Scripts\python.exe main.py`).
- **Update:** `guncelle.bat` — pulls the latest version (if the folder is a git clone) and updates packages; `veriler` and `modeller` are kept.

Python 3.10 or newer is required. On first start the interface language follows the Windows language; it can be changed in Settings (the program restarts).

## Usage

1. **Folder scan:** add folders with **Add**, check the ones to scan (subfolders included). Choose model and language, then **Scan and create subtitles**. Already processed, unchanged videos are skipped.
2. **Word search / SRT:** search all subtitles. Case and Turkish-character insensitive (`dusunce` finds `Düşünce`); prefix matching by default, **Whole words only** to turn it off. **Scope**: *Same video* (words may be on different lines) or *Same line*. Filters: folder, duration, size. Preview frames are generated in the background.
3. **Details** (or double-click): full subtitle with an embedded player starting at the matched second; open in VLC at that second, copy text, save SRT.
4. **Video list:** paged list of all recorded videos with type, duration, size, resolution, line count, model/language and MD5. Sort by clicking headers, reprocess selected or filtered videos with another model, **Check broken links** to relink moved files.
5. **Settings:** interface language, processing unit (automatic / GPU / CPU) and the **automatic scan scheduler** (e.g. 20:00 – 07:00): the scan starts at the start time; at the end time the current video is finished and the rest waits for the next night. The program must stay open; sleep is prevented during scans.

Moved or renamed videos are relinked automatically when the MD5 (or size and date) matches; their subtitles are kept and not reprocessed.

## Folder layout

```text
main.py            entry point
arsiv/             program code (arayuz = UI, isci = worker, veritabani = database, ceviri = translations ...)
tests/             unit tests
varliklar/         icon
veriler/           altyazilar.sqlite3, ayarlar.ini, onizlemeler/ (not published)
modeller/          downloaded speech models (not published)
```

The code uses Turkish identifiers. Interface strings are Turkish keys passed to `_t()`; English texts are in `arsiv/ceviri_en.py`.

## Tests

```
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests do not download a model; speech recognition is mocked and a temporary database is used. `tests/test_ceviri.py` fails if an interface string has no English translation.

## License

MIT — see [LICENSE](LICENSE). Speech recognition engine: [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
