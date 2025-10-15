import io
import re
import pandas as pd
import streamlit as st
from typing import List, Dict, Optional, Tuple

# ---------------- UI ----------------
st.set_page_config(page_title="Čitač nalaza – v3 (univerzalni)", page_icon="🧪", layout="wide")
st.title("🧪 Čitač laboratorijskih nalaza – v3")
st.caption("Univerzalni parser za sve formate laboratorijskih nalaza (PDF, slike, OCR)")

with st.expander("ℹ️ Kako radi"):
    st.markdown("""
**Univerzalni parser:**
1) **Smart parsing**: Prepoznaje različite formate (državni sistem, privatni laboratoriji)
2) **OCR podrška**: Radi sa skeniranim PDF-ovima i slikama (PNG, JPG, TIFF, BMP)
3) **Validacija**: Filtrira samo prave laboratorijske analite
4) **Deduplikacija**: Uklanja duplikate i zadržava najbolje rezultate
5) **Status**: Automatski računa da li je vrednost u referentnom opsegu

**Podržani formati:**
- PDF (tekstualni i skenirani)
- Slike: PNG, JPG, JPEG, TIFF, BMP, GIF
- Automatski OCR za skenirane dokumente

**Za OCR funkcionalnost:**
```bash
pip install pytesseract pillow pymupdf
```
""")

# ---------------- PDF text extraction ----------------
def extract_pdf_text_native(file_bytes: bytes) -> str:
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for p in pdf.pages:
                text += (p.extract_text() or "") + "\n"
        if text.strip():
            return text
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader
        r = PdfReader(io.BytesIO(file_bytes))
        for p in r.pages:
            text += (p.extract_text() or "") + "\n"
        if text.strip():
            return text
    except Exception:
        pass
    return ""

# ---------------- OCR for images ----------------
def extract_text_from_image(file_bytes: bytes) -> str:
    """Extract text from image using OCR"""
    try:
        from PIL import Image
        import pytesseract
        import os
        
        # Try to find Tesseract executable
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', '')),
            'tesseract'  # If in PATH
        ]
        
        tesseract_found = False
        for path in tesseract_paths:
            if os.path.exists(path) or path == 'tesseract':
                try:
                    pytesseract.pytesseract.tesseract_cmd = path
                    pytesseract.get_tesseract_version()
                    tesseract_found = True
                    break
                except:
                    continue
        
        if not tesseract_found:
            st.error("""
            **Tesseract OCR nije instaliran!**
            
            **Instaliraj Tesseract OCR:**
            1. Idi na: https://github.com/tesseract-ocr/tesseract/releases
            2. Preuzmi najnoviju verziju za Windows
            3. Instaliraj sa default opcijama
            4. Restartuj aplikaciju
            
            **Alternativno:**
            ```bash
            # Preko Chocolatey
            choco install tesseract
            
            # Preko Scoop
            scoop install tesseract
            ```
            """)
            return ""
        
        # Open image
        image = Image.open(io.BytesIO(file_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract text using OCR
        text = pytesseract.image_to_string(image, lang='eng+srp')
        return text.strip()
    except ImportError as e:
        st.error(f"OCR biblioteke nisu instalirane. Instaliraj: pip install pytesseract pillow")
        return ""
    except Exception as e:
        st.error(f"OCR greška: {str(e)}")
        return ""

def extract_text_from_pdf_with_ocr(file_bytes: bytes) -> str:
    """Extract text from PDF using OCR (for scanned PDFs)"""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        import pytesseract
        import os
        
        # Try to find Tesseract executable
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', '')),
            'tesseract'  # If in PATH
        ]
        
        tesseract_found = False
        for path in tesseract_paths:
            if os.path.exists(path) or path == 'tesseract':
                try:
                    pytesseract.pytesseract.tesseract_cmd = path
                    pytesseract.get_tesseract_version()
                    tesseract_found = True
                    break
                except:
                    continue
        
        if not tesseract_found:
            st.error("""
            **Tesseract OCR nije instaliran!**
            
            **Instaliraj Tesseract OCR:**
            1. Idi na: https://github.com/tesseract-ocr/tesseract/releases
            2. Preuzmi najnoviju verziju za Windows
            3. Instaliraj sa default opcijama
            4. Restartuj aplikaciju
            """)
            return ""
        
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # First try to extract text normally
            page_text = page.get_text()
            if page_text.strip():
                text += page_text + "\n"
            else:
                # If no text, use OCR on the page image
                mat = fitz.Matrix(2, 2)  # Scale up for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to PIL Image
                image = Image.open(io.BytesIO(img_data))
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # OCR
                ocr_text = pytesseract.image_to_string(image, lang='eng+srp')
                text += ocr_text + "\n"
        
        doc.close()
        return text.strip()
    except ImportError as e:
        st.error(f"OCR biblioteke nisu instalirane. Instaliraj: pip install pytesseract pillow pymupdf")
        return ""
    except Exception as e:
        st.error(f"PDF OCR greška: {str(e)}")
        return ""

# ---------------- Smart Parser ----------------
class LabResultParser:
    def __init__(self):
        # Poznati analiti
        self.known_analytes = {
            "hemoglobin", "hb", "eritrociti", "rbc", "leukociti", "wbc", "trombociti", "plt",
            "hematokrit", "hct", "glukoza", "glucose", "urea", "kreatinin", "creatinine",
            "alt", "gpt", "ast", "got", "ggt", "gamma gt", "holesterol", "cholesterol",
            "hdl", "ldl", "trigliceridi", "triglycerides", "natrijum", "na", "kalijum", "k",
            "kalcijum", "ca", "neutrofili", "neutrophils", "limfociti", "lymphocytes",
            "monociti", "monocytes", "eozinofili", "eosinophils", "bazofili", "basophils",
            "mcv", "mch", "mchc", "rdw", "pdw", "mpv", "pct", "p-lcr", "ig", "sedimentacija",
            "protrombinsko", "inr", "aptt", "fibrinogen", "bilirubin", "urobilinogen",
            "glukoza u urinu", "eritrociti u urinu", "proteini u urinu", "ketoni u urinu",
            "nitriti", "leukociti u urinu", "krv u urinu", "ph urina", "specifina težina"
        }
        
        # Reči koje treba preskočiti
        self.skip_words = {
            "laboratorijska", "dijagnostika", "uzorkovanja", "vrijeme", "datum", "pacijent", 
            "doktor", "dr", "serum", "plazma", "citrat", "punkt", "protokola", "br.",
            "aligrudić", "golubovci", "filip", "mara", "džomić", "qo", "med", "dijag",
            "normalan", "negativan", "pozitivan", "granulociti", "epitelne", "cel",
            "neskvamozne", "bubrežni", "epitel", "elije", "težina", "specifina"
        }
        
        # Regex patterni
        self.num_pattern = r"[-+]?\d+(?:[.,]\d+)?"
        self.qual_pattern = r"(?:Negativan|Normalan|Pozitivan)"
        self.unit_pattern = r"(?:10[\*\^]\d+\/[A-Za-z]+|[A-Za-z%\/\*\.\-\^]+)"
        self.range_pattern = rf"(?:{self.num_pattern}\s*[~\-]\s*{self.num_pattern}|<\s*{self.num_pattern}|>\s*{self.num_pattern}|{self.qual_pattern})"
    
    def is_valid_analyte(self, name: str) -> bool:
        """Proverava da li je naziv valjan analit"""
        if not name or len(name.strip()) < 2:
            return False
        
        name_lower = name.lower().strip()
        
        # Preskoči ako sadrži skip reči
        for skip_word in self.skip_words:
            if skip_word in name_lower:
                return False
        
        # Proveri da li sadrži poznate analite
        for analyte in self.known_analytes:
            if analyte in name_lower:
                return True
        
        # Proveri da li je kratak i smislen (1-3 reči)
        words = name_lower.split()
        if len(words) <= 3 and all(len(w) > 1 for w in words):
            if not all(w.isdigit() or len(w) < 3 for w in words):
                return True
        
        return False
    
    def parse_value(self, val_str: str) -> Tuple[Optional[float], Optional[str]]:
        """Parsira vrednost - vraća (numerička_vrednost, kvalitativna_vrednost)"""
        if not val_str:
            return None, None
        
        val_str = val_str.strip()
        
        # Proveri da li je kvalitativna vrednost
        if re.fullmatch(self.qual_pattern, val_str):
            return None, val_str
        
        # Pokušaj da parsiraš numeričku vrednost
        try:
            # Zameni zarez tačkom
            val_clean = val_str.replace(",", ".")
            return float(val_clean), None
        except:
            return None, val_str
    
    def is_qualitative_result(self, analyte: str, value: str) -> bool:
        """Proverava da li je kvalitativni rezultat (npr. urin analiza)"""
        qualitative_analytes = {
            "glukoza u urinu", "eritrociti u urinu", "proteini u urinu", 
            "bilirubin u urinu", "urobilinogen u urinu", "krv u urinu",
            "ketoni u urinu", "nitriti", "leukociti u urinu"
        }
        
        analyte_lower = analyte.lower()
        for qual_analyte in qualitative_analytes:
            if qual_analyte in analyte_lower:
                return True
        return False
    
    def parse_reference(self, ref_str: str) -> Tuple[Optional[float], Optional[float], str, Optional[str]]:
        """Parsira referentne vrednosti - vraća (low, high, type, qual_ref)"""
        if not ref_str:
            return None, None, "none", None
        
        ref_str = ref_str.strip()
        
        # Kvalitativna referenca
        if re.fullmatch(self.qual_pattern, ref_str):
            return None, None, "qual", ref_str
        
        # Range format (npr. "4.5-6.2")
        range_match = re.match(rf"^{self.num_pattern}\s*[~\-]\s*{self.num_pattern}$", ref_str)
        if range_match:
            parts = re.split(r"[~\-]", ref_str)
            low = float(parts[0].strip().replace(",", "."))
            high = float(parts[1].strip().replace(",", "."))
            return low, high, "range", None
        
        # Less than format (npr. "<10")
        lt_match = re.match(rf"^<\s*{self.num_pattern}$", ref_str)
        if lt_match:
            high = float(lt_match.group(0).split("<")[1].strip().replace(",", "."))
            return None, high, "<", None
        
        # Greater than format (npr. ">5")
        gt_match = re.match(rf"^>\s*{self.num_pattern}$", ref_str)
        if gt_match:
            low = float(gt_match.group(0).split(">")[1].strip().replace(",", "."))
            return low, None, ">", None
        
        return None, None, "none", None
    
    def calculate_status(self, val_num: Optional[float], val_qual: Optional[str], 
                        ref_low: Optional[float], ref_high: Optional[float], 
                        ref_type: str, qual_ref: Optional[str]) -> str:
        """Računa status vrednosti"""
        if val_num is not None:
            if ref_type == "range" and ref_low is not None and ref_high is not None:
                if val_num < ref_low:
                    return "⬇️ ispod"
                elif val_num > ref_high:
                    return "⬆️ iznad"
                else:
                    return "✅ u referentnom"
            elif ref_type == "<" and ref_high is not None:
                return "✅ u referentnom" if val_num < ref_high else "⬆️ iznad"
            elif ref_type == ">" and ref_low is not None:
                return "✅ u referentnom" if val_num > ref_low else "⬇️ ispod"
            else:
                return ""
        
        if val_qual is not None and qual_ref is not None:
            return "✅ u referentnom" if val_qual == qual_ref else "⚠️ odstupanje"
        
        return ""
    
    def clean_analyte_name(self, name: str) -> Tuple[str, str]:
        """Čisti naziv analita i određuje tip"""
        name = name.strip()
        
        # Ukloni prefikse
        if name.lower().startswith(("k-", "s-")):
            name = name[2:].strip()
        
        # Normalizuj razmake
        name = re.sub(r"\s+", " ", name.replace("aps.", "aps")).strip()
        
        typ = ""
        
        # Proveri tip
        if name.endswith("%"):
            typ = "%"
            name = name[:-1].strip()
        elif name.lower().endswith(" aps"):
            typ = "aps"
            name = name[:-3].strip()
        
        return name, typ
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """Parsira jednu liniju teksta"""
        if not line.strip():
            return None
        
        # Različiti patterni za različite formate
        patterns = [
            # Format: Analit Vrijednost Jedinica Ref
            rf"^(?P<analyte>[A-Za-zČĆŠĐŽčćšđž][A-Za-zČĆŠĐŽčćšđž\s\.\-%]+?)\s+(?P<value>{self.num_pattern}|{self.qual_pattern})\s+(?P<unit>{self.unit_pattern})?\s*(?P<ref>{self.range_pattern})?\s*$",
            
            # Format: Analit Vrijednost Jedinica (bez ref)
            rf"^(?P<analyte>[A-Za-zČĆŠĐŽčćšđž][A-Za-zČĆŠĐŽčćšđž\s\.\-%]+?)\s+(?P<value>{self.num_pattern}|{self.qual_pattern})\s+(?P<unit>{self.unit_pattern})\s*$",
            
            # Format: Vrijednost Jedinica Analit
            rf"^(?P<value>{self.num_pattern}|{self.qual_pattern})\s+(?P<unit>{self.unit_pattern})\s+(?P<analyte>[A-Za-zČĆŠĐŽčćšđž][A-Za-zČĆŠĐŽčćšđž\s\.\-%]+?)\s*$",
            
            # Format: Analit Vrijednost (bez jedinice)
            rf"^(?P<analyte>[A-Za-zČĆŠĐŽčćšđž][A-Za-zČĆŠĐŽčćšđž\s\.\-%]+?)\s+(?P<value>{self.num_pattern}|{self.qual_pattern})\s*$"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line.strip())
            if match:
                groups = match.groupdict()
                analyte = groups.get("analyte", "").strip()
                value = groups.get("value", "").strip()
                unit = groups.get("unit", "").strip()
                ref = groups.get("ref", "").strip()
                
                # Validiraj analit
                if not self.is_valid_analyte(analyte):
                    continue
                
                # Parsiraj vrednost
                val_num, val_qual = self.parse_value(value)
                
                # Specijalna logika za kvalitativne rezultate
                if self.is_qualitative_result(analyte, value):
                    # Za kvalitativne rezultate, vrednost je kvalitativna, ne jedinica
                    if val_qual and unit.lower() in ["negativan", "normalan", "pozitivan"]:
                        unit = ""  # Jedinica je zapravo vrednost
                        val_qual = unit
                
                # Parsiraj referencu
                ref_low, ref_high, ref_type, qual_ref = self.parse_reference(ref)
                
                # Čisti naziv analita
                clean_name, typ = self.clean_analyte_name(analyte)
                
                # Računaj status
                status = self.calculate_status(val_num, val_qual, ref_low, ref_high, ref_type, qual_ref)
                
                return {
                    "Analit": clean_name,
                    "Tip": typ,
                    "Vrijednost": val_num if val_num is not None else val_qual,
                    "Jedinica": unit,
                    "Ref_low": ref_low,
                    "Ref_high": ref_high,
                    "Ref_tip": ref_type,
                    "Ref_kval": qual_ref,
                    "Flag": "",
                    "Status": status,
                    "Izvor": "smart",
                    "Linija": line
                }
        
        return None
    
    def parse_text(self, text: str) -> pd.DataFrame:
        """Parsira ceo tekst"""
        results = []
        
        # Podeli tekst na linije
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Pokušaj da podeliš na kolone (ako su razdvojene sa 2+ razmaka)
            parts = re.split(r"\s{2,}", line)
            if len(parts) > 1:
                lines.extend([p.strip() for p in parts if p.strip()])
            else:
                lines.append(line)
        
        # Parsiraj svaku liniju
        for line in lines:
            result = self.parse_line(line)
            if result:
                results.append(result)
        
        if not results:
            return pd.DataFrame(columns=["Analit","Tip","Vrijednost","Jedinica","Ref_low","Ref_high","Ref_tip","Ref_kval","Flag","Status","Izvor","Linija"])
        
        df = pd.DataFrame(results)
        
        # Deduplikacija - prioritet rezultatima sa referentnim vrednostima
        df["_priority"] = df[["Ref_low", "Ref_high", "Ref_tip"]].notna().sum(axis=1)
        df["_has_unit"] = df["Jedinica"].notna() & (df["Jedinica"] != "")
        df = df.sort_values(["_priority", "_has_unit", "Analit"], ascending=[False, False, True])
        df = df.drop_duplicates(subset=["Analit"], keep="first")
        df = df.drop(columns=["_priority", "_has_unit"])
        
        return df

# ---------------- Main App ----------------
parser = LabResultParser()

# Sidebar
with st.sidebar:
    st.header("⚙️ Podešavanja")
    show_preview = st.checkbox("Prikaži preview teksta", value=True)
    st.markdown("---")
    st.subheader("Unos")
    upload_mode = st.radio("Izvor podataka", ["PDF/Slike", "Tekst (paste)"])
    
    folder_path = ""
    if upload_mode == "PDF/Slike":
        folder_path = st.text_input("📁 Folder sa PDF-ovima/slikama (opciono)", "")
        st.caption("Ako uneseš folder, svi PDF i slike (.pdf, .png, .jpg, .jpeg, .tiff, .bmp) biće učitani.")

# Main input
uploaded_files = None
text_input_fallback = None

if upload_mode == "Tekst (paste)":
    text_input_fallback = st.text_area("📋 Zalijepi tekst nalaza", "", height=200)
else:
    uploaded_files = st.file_uploader("📤 Učitaj PDF/Slike (više datoteka dozvoljeno)", 
                                     type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "gif"], 
                                     accept_multiple_files=True,
                                     help="Podržani formati: PDF (tekstualni i skenirani), PNG, JPG, JPEG, TIFF, BMP, GIF")

# Processing
dataframes = []

# Debug info
if uploaded_files:
    st.write(f"📁 Uploaded files: {len(uploaded_files)}")
    for f in uploaded_files:
        st.write(f"  - {f.name} ({f.type})")

if upload_mode == "Tekst (paste)":
    if (text_input_fallback or "").strip():
        text = text_input_fallback
        if show_preview:
            st.text_area("📄 Tekst iz nalaza (preview)", text, height=230)
        
        df = parser.parse_text(text)
        if not df.empty:
            dataframes.append(df)
        else:
            st.warning("⚠️ Nije prepoznat nijedan red iz zalijepljenog teksta.")
    else:
        st.info("📋 Zalijepi tekst nalaza u polje sa lijeve strane.")
else:
    if uploaded_files or (folder_path or "").strip():
        # Pripremi zajedničku listu fajlova
        selected_files = []
        if uploaded_files:
            selected_files.extend(uploaded_files)
        if (folder_path or "").strip():
            import os, glob
            class _LocalFile:
                def __init__(self, path):
                    self.name = os.path.basename(path)
                    self._path = path
                def read(self):
                    with open(self._path, "rb") as fh:
                        return fh.read()
            # Add PDF files
            for p in sorted(glob.glob(os.path.join(folder_path, "*.pdf"))):
                selected_files.append(_LocalFile(p))
            
            # Add image files
            for ext in ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.bmp"]:
                for p in sorted(glob.glob(os.path.join(folder_path, ext))):
                    selected_files.append(_LocalFile(p))

        for f in selected_files:
            by = f.read()
            file_ext = f.name.lower().split('.')[-1] if '.' in f.name else ''
            
            # Debug info
            st.write(f"🔍 Processing: {f.name} (type: {file_ext})")
            
            with st.spinner(f"⏳ Čitam {f.name}..."):
                text = ""
                
                if file_ext == 'pdf':
                    # Try normal PDF extraction first
                    text = extract_pdf_text_native(by)
                    
                    # If no text, try OCR
                    if not text.strip():
                        st.info(f"📷 {f.name}: Pokušavam OCR...")
                        text = extract_text_from_pdf_with_ocr(by)
                else:
                    # Image file - use OCR
                    st.info(f"📷 {f.name}: Koristim OCR...")
                    text = extract_text_from_image(by)
            
            if not text.strip():
                st.error(f"❌ {f.name}: Nije moguće izvući tekst.")
                continue
                
            if show_preview:
                with st.expander(f"📄 Tekst: {f.name}"):
                    st.text_area("", text, height=200)
            
            df = parser.parse_text(text)
            if not df.empty:
                dataframes.append(df)
            else:
                st.warning(f"⚠️ {f.name}: Nije prepoznat nijedan red.")
    else:
        st.info("📂 Učitaj jedan ili više PDF-ova/slika ili pređi na 'Tekst (paste)'.")

# Results
if dataframes:
    combined = pd.concat(dataframes, ignore_index=True)
    view_cols = ["Analit","Tip","Vrijednost","Jedinica","Ref_low","Ref_high","Ref_tip","Status","Izvor"]
    
    st.subheader("📊 Izvučeni podaci")
    st.dataframe(combined[view_cols], use_container_width=True)

    st.markdown("**Filtriraj odstupanja:**")
    only_out = st.checkbox("Prikaži samo van referentnog", value=False)
    filt = combined[combined["Status"].str.contains("⬆️|⬇️|⚠️", na=False)] if only_out else combined
    st.dataframe(filt[view_cols], use_container_width=True)

    # Summary
    st.markdown("---")
    st.subheader("📈 Sažetak statusa")
    counts = combined["Status"].fillna("").replace({"": "Bez statusa"}).value_counts()
    st.bar_chart(counts)

    # Downloads
    st.subheader("⬇️ Preuzimanja")
    csv_bytes = combined.to_csv(index=False).encode("utf-8")
    st.download_button("Preuzmi CSV", data=csv_bytes, file_name="lab_extract_v3.csv", mime="text/csv")
    
    import io as _io
    out = _io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as w:
        combined.to_excel(w, index=False, sheet_name="Nalazi")
    st.download_button("Preuzmi Excel", data=out.getvalue(),
                       file_name="lab_extract_v3.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Per-file export
    if len(dataframes) > 1:
        with st.expander("Per-file export"):
            for i, dfi in enumerate(dataframes):
                c_bytes = dfi.to_csv(index=False).encode("utf-8")
                fname = f"file_{i+1}"
                st.download_button(f"CSV – {fname}", data=c_bytes, file_name=f"lab_extract_{fname}_v3.csv", mime="text/csv")

else:
    st.info("📂 Učitaj jedan ili više tekstualnih PDF-ova ili pređi na 'Tekst (paste)'.")
