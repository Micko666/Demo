# 🧪 Čitač laboratorijskih nalaza

Univerzalni parser za sve formate laboratorijskih nalaza sa OCR podrškom.

## 🚀 Funkcionalnosti

- **Smart parsing**: Prepoznaje različite formate (državni sistem, privatni laboratoriji)
- **OCR podrška**: Radi sa skeniranim PDF-ovima i slikama
- **Validacija**: Filtrira samo prave laboratorijske analite
- **Deduplikacija**: Uklanja duplikate i zadržava najbolje rezultate
- **Status**: Automatski računa da li je vrednost u referentnom opsegu

## 📋 Podržani formati

- **PDF**: Tekstualni i skenirani
- **Slike**: PNG, JPG, JPEG, TIFF, BMP, GIF
- **Automatski OCR** za skenirane dokumente

## 🛠️ Instalacija

1. Kloniraj repozitorijum:
```bash
git clone https://github.com/Micko666/Demo.git
cd Demo
```

2. Instaliraj zavisnosti:
```bash
pip install -r requirements.txt
```

3. Pokreni aplikaciju:
```bash
streamlit run app_v3.py
```

## 📖 Korišćenje

1. **PDF/Slike mod**: Učitaj PDF fajlove ili slike laboratorijskih nalaza
2. **Tekst mod**: Zalijepi tekst nalaza direktno
3. **Folder mod**: Unesi putanju foldera sa PDF-ovima i slikama

## 🔧 OCR biblioteke

Za OCR funkcionalnost su potrebne dodatne biblioteke:

```bash
pip install pytesseract pillow pymupdf
```

## 📊 Rezultati

Aplikacija generiše:
- **CSV fajl** sa svim analitima
- **Excel fajl** sa formatiranim podacima
- **Status analizu** (normalan/iznad/ispod referentnog)
- **Per-file export** za batch processing

## 🧪 CLI mod

Za batch processing bez UI:

```bash
python app_v3.py --cli "folder_path" "output.csv"
```

## 📝 Verzije

- **v1**: Osnovni parser
- **v2**: Poboljšana validacija i deduplikacija
- **v3**: OCR podrška i univerzalni parser
