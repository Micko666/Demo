# 📋 Instrukcije za GitHub upload

## 🚀 Kako uploadovati na GitHub

1. **Idi na GitHub repozitorijum**: https://github.com/Micko666/Demo.git
2. **Klikni "Upload files"** ili "Add file" → "Upload files"
3. **Drag & drop** sve fajlove iz foldera ili uploaduj `lab_reader_final.zip`
4. **Commit changes** sa porukom: "Add Lab Reader v3 with OCR support"

## 📁 Fajlovi za upload

- `app_v3.py` - Glavna aplikacija
- `requirements.txt` - Python zavisnosti
- `README.md` - Dokumentacija
- `setup.py` - Setup za instalaciju
- `.gitignore` - Git ignore fajl
- `run.bat` - Windows batch fajl
- `run.sh` - Linux/Mac skripta
- `izvjestajPDF-1.pdf` - Test PDF
- `DurovicMihailo_615027a575882.pdf` - Test PDF

## 🧪 Kako pokrenuti

### Windows:
```bash
# Opcija 1: Koristi batch fajl
run.bat

# Opcija 2: Manualno
pip install -r requirements.txt
python -m streamlit run app_v3.py
```

### Linux/Mac:
```bash
# Opcija 1: Koristi shell skriptu
chmod +x run.sh
./run.sh

# Opcija 2: Manualno
pip install -r requirements.txt
python -m streamlit run app_v3.py
```

## 🔧 OCR biblioteke

Za OCR funkcionalnost:
```bash
pip install pytesseract pillow pymupdf
```

## 📊 Funkcionalnosti

- ✅ **PDF parsing** (tekstualni i skenirani)
- ✅ **Image OCR** (PNG, JPG, JPEG, TIFF, BMP, GIF)
- ✅ **Smart validation** (filtrira samo prave analite)
- ✅ **Deduplication** (uklanja duplikate)
- ✅ **Status calculation** (normalan/iznad/ispod)
- ✅ **CSV/Excel export**
- ✅ **Batch processing**
- ✅ **CLI mode**

## 🌐 Aplikacija

Kada se pokrene, aplikacija je dostupna na: **http://localhost:8501**
