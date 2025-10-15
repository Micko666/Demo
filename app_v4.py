import io
import re
import pandas as pd
import streamlit as st
from typing import List, Dict, Optional, Tuple
import os

# ---------------- UI Setup ----------------
st.set_page_config(
    page_title="Lab Reader", 
    page_icon="🧪", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better design
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .upload-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border: 2px dashed #dee2e6;
        margin: 1rem 0;
    }
    .result-section {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ---------------- Header ----------------
st.markdown("""
<div class="main-header">
    <h1>🧪 Lab Reader</h1>
    <p>Univerzalni parser za laboratorijske nalaze sa OCR podrškom</p>
</div>
""", unsafe_allow_html=True)

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
            st.warning("⚠️ Tesseract OCR nije instaliran. Instaliraj ga za OCR funkcionalnost.")
            return ""
        
        # Open image
        image = Image.open(io.BytesIO(file_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract text using OCR
        text = pytesseract.image_to_string(image, lang='eng+srp')
        return text.strip()
    except ImportError:
        st.error("OCR biblioteke nisu instalirane. Instaliraj: pip install pytesseract pillow")
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
            st.warning("⚠️ Tesseract OCR nije instaliran. Instaliraj ga za OCR funkcionalnost.")
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
    except ImportError:
        st.error("OCR biblioteke nisu instalirane. Instaliraj: pip install pytesseract pillow pymupdf")
        return ""
    except Exception as e:
        st.error(f"PDF OCR greška: {str(e)}")
        return ""

# ---------------- Smart Parser ----------------
class LabResultParser:
    def __init__(self):
        # Poznati analiti
        self.known_analytes = {
            "glukoza", "hemoglobin", "hematokrit", "leukociti", "eritrociti", "trombociti",
            "kreatinin", "ureja", "bilirubin", "alt", "ast", "ggt", "alkalna fosfataza",
            "ldh", "ck", "troponin", "crp", "esr", "feritin", "vitamin d", "b12", "folna kiselina",
            "tsh", "ft3", "ft4", "testosteron", "estradiol", "progesteron", "insulin",
            "hba1c", "lipidi", "holesterol", "trigliceridi", "hdl", "ldl", "apolipoprotein",
            "sodium", "kalijum", "kalcijum", "fosfor", "magnezijum", "kloridi", "bikarbonati",
            "ph", "pco2", "po2", "hco3", "base excess", "laktat", "glukoza u urinu",
            "proteini u urinu", "eritrociti u urinu", "leukociti u urinu", "nitriti",
            "ketoni u urinu", "bilirubin u urinu", "urobilinogen u urinu", "krv u urinu"
        }
        
        # Reči koje treba preskočiti
        self.skip_words = {
            "datum", "vrijeme", "ime", "prezime", "jmbg", "adresa", "telefon", "email",
            "doktor", "dr", "prof", "država", "grad", "ulica", "broj", "kat", "stan",
            "laboratorij", "analiza", "rezultat", "vrijednost", "jedinica", "referenca",
            "normalan", "povišen", "snižen", "kritičan", "urgentno", "hitno", "redovno",
            "kontrola", "pregled", "dijagnoza", "terapija", "lijek", "doza", "tableta",
            "kapsula", "sirup", "injeksija", "infuzija", "operacija", "hirurgija",
            "bolnica", "klinika", "ambulanta", "ordinacija", "sestra", "tehničar",
            "direktor", "upravnik", "sekretar", "administrator", "račun", "faktura",
            "plaćanje", "osiguranje", "kartica", "bankovni", "transfer", "depozit"
        }
        
        # Regex patterns
        self.num_pattern = r'(\d+[,.]?\d*)'
        self.qual_pattern = r'^(pozitivno|negativno|normalno|povišeno|sniženo|kritično|da|ne|\+|\-|pos|neg|norm|elevated|low|high|critical)$'
        self.unit_pattern = r'(g/dl|mg/dl|μg/dl|ng/ml|pg/ml|U/L|IU/L|mmol/L|μmol/L|%|cells/μL|×10³/μL|×10⁶/μL|mm/h|mg/L|ng/dL|pmol/L|mIU/L|μIU/mL)'
        self.range_pattern = r'(\d+[,.]?\d*)\s*-\s*(\d+[,.]?\d*)'
    
    def is_valid_analyte(self, name: str) -> bool:
        """Check if analyte name is valid"""
        if not name or len(name.strip()) < 2:
            return False
        
        name_lower = name.lower().strip()
        
        # Skip if contains skip words
        for skip_word in self.skip_words:
            if skip_word in name_lower:
                return False
        
        # Check if contains known analytes
        for analyte in self.known_analytes:
            if analyte in name_lower:
                return True
        
        # Check if it's a reasonable analyte name (2-3 words, not all numbers)
        words = name_lower.split()
        if len(words) <= 3 and all(len(w) > 1 for w in words):
            if not all(w.isdigit() or len(w) < 3 for w in words):
                return True
        
        return False
    
    def parse_value(self, val_str: str) -> Tuple[Optional[float], Optional[str]]:
        """Parse value string into numeric or qualitative value"""
        if not val_str:
            return None, None
        
        val_str = val_str.strip()
        
        # Check if it's qualitative
        if re.fullmatch(self.qual_pattern, val_str, re.IGNORECASE):
            return None, val_str
        
        try:
            # Try to convert to float
            val_clean = val_str.replace(",", ".")
            return float(val_clean), None
        except:
            return None, val_str
    
    def is_qualitative_result(self, analyte: str, value: str) -> bool:
        """Check if result is qualitative"""
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
    
    def parse_reference(self, ref_str: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Parse reference range"""
        if not ref_str:
            return None, None, None
        
        # Try different patterns
        patterns = [
            r'(\d+[,.]?\d*)\s*-\s*(\d+[,.]?\d*)',  # 3.5-5.0
            r'(\d+[,.]?\d*)\s*do\s*(\d+[,.]?\d*)',  # 3.5 do 5.0
            r'(\d+[,.]?\d*)\s*-\s*(\d+[,.]?\d*)\s*(\w+)',  # 3.5-5.0 g/dl
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ref_str)
            if match:
                try:
                    low = float(match.group(1).replace(",", "."))
                    high = float(match.group(2).replace(",", "."))
                    unit = match.group(3) if len(match.groups()) > 2 else None
                    return low, high, unit
                except:
                    continue
        
        return None, None, None
    
    def clean_analyte_name(self, name: str) -> str:
        """Clean analyte name"""
        if not name:
            return ""
        
        # Remove extra spaces and clean up
        name = re.sub(r'\s+', ' ', name.strip())
        
        # Remove common prefixes/suffixes
        name = re.sub(r'^(test|analiza|vrijednost|rezultat)\s+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(test|analiza|vrijednost|rezultat)$', '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
    def calculate_status(self, value: float, ref_low: float, ref_high: float) -> str:
        """Calculate status based on value and reference range"""
        if value < ref_low:
            return "Sniženo"
        elif value > ref_high:
            return "Povišeno"
        else:
            return "Normalno"
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """Parse a single line for lab results"""
        if not line or len(line.strip()) < 3:
            return None
        
        line = line.strip()
        
        # Try different patterns
        patterns = [
            # Pattern 1: Analyte Value Unit Ref
            r'^([^0-9]+?)\s+(\d+[,.]?\d*)\s+(\w+)\s+(\d+[,.]?\d*)\s*-\s*(\d+[,.]?\d*)$',
            # Pattern 2: Analyte Value Unit
            r'^([^0-9]+?)\s+(\d+[,.]?\d*)\s+(\w+)$',
            # Pattern 3: Value Unit Analyte
            r'^(\d+[,.]?\d*)\s+(\w+)\s+([^0-9]+?)$',
            # Pattern 4: Analyte Value
            r'^([^0-9]+?)\s+(\d+[,.]?\d*)$',
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, line)
            if match:
                groups = match.groups()
                
                if i == 0:  # Pattern 1: Analyte Value Unit Ref
                    analyte, value, unit, ref_low, ref_high = groups
                    ref_low = float(ref_low.replace(",", "."))
                    ref_high = float(ref_high.replace(",", "."))
                elif i == 1:  # Pattern 2: Analyte Value Unit
                    analyte, value, unit = groups
                    ref_low, ref_high = None, None
                elif i == 2:  # Pattern 3: Value Unit Analyte
                    value, unit, analyte = groups
                    ref_low, ref_high = None, None
                else:  # Pattern 4: Analyte Value
                    analyte, value = groups
                    unit = None
                    ref_low, ref_high = None, None
                
                # Clean analyte name
                analyte = self.clean_analyte_name(analyte)
                
                # Validate analyte
                if not self.is_valid_analyte(analyte):
                    return None
                
                # Parse value
                numeric_value, qual_value = self.parse_value(value)
                
                # Handle qualitative results
                if self.is_qualitative_result(analyte, value):
                    if unit and unit.lower() in ['pozitivno', 'negativno', 'normalno', 'povišeno', 'sniženo']:
                        qual_value = unit
                        unit = None
                
                # Calculate status
                status = None
                if numeric_value is not None and ref_low is not None and ref_high is not None:
                    status = self.calculate_status(numeric_value, ref_low, ref_high)
                elif qual_value:
                    status = "Kvalitativno"
                
                return {
                    "Analit": analyte,
                    "Vrijednost": numeric_value if numeric_value is not None else qual_value,
                    "Jedinica": unit,
                    "Ref_low": ref_low,
                    "Ref_high": ref_high,
                    "Status": status
                }
        
        return None
    
    def parse_text(self, text: str) -> pd.DataFrame:
        """Parse text and return DataFrame"""
        if not text:
            return pd.DataFrame()
        
        lines = text.split('\n')
        results = []
        
        for line in lines:
            result = self.parse_line(line)
            if result:
                results.append(result)
        
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        
        # Enhanced deduplication
        if not df.empty:
            # Add priority columns
            df["_priority"] = df[["Ref_low", "Ref_high"]].notna().sum(axis=1)
            df["_has_unit"] = df["Jedinica"].notna() & (df["Jedinica"] != "")
            
            # Sort by priority (reference values first, then units, then alphabetically)
            df = df.sort_values(["_priority", "_has_unit", "Analit"], ascending=[False, False, True])
            
            # Remove duplicates, keeping the first (highest priority) entry
            df = df.drop_duplicates(subset=["Analit"], keep="first")
            
            # Remove helper columns
            df = df.drop(columns=["_priority", "_has_unit"])
        
        return df

# ---------------- Main UI ----------------
# Sidebar
st.sidebar.markdown("### ⚙️ Postavke")
upload_mode = st.sidebar.radio(
    "Izaberite način unosa:",
    ["📄 PDF/Slike", "📝 Tekst"],
    help="PDF/Slike: Učitaj fajlove sa OCR podrškom\nTekst: Zalijepi tekst direktno"
)

# Main content
if upload_mode == "📄 PDF/Slike":
    st.markdown("""
    <div class="upload-section">
        <h3>📤 Učitaj laboratorijske nalaze</h3>
        <p>Podržani formati: PDF (tekstualni i skenirani), PNG, JPG, JPEG, TIFF, BMP, GIF</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "Izaberite fajlove:",
        type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "gif"],
        accept_multiple_files=True,
        help="Možete učitati više fajlova odjednom"
    )
    
    if uploaded_files:
        st.success(f"✅ Učitano {len(uploaded_files)} fajlova")
        
        # Process files
        parser = LabResultParser()
        all_results = []
        
        for file in uploaded_files:
            with st.spinner(f"Obrađujem {file.name}..."):
                # Determine file type
                if file.name.lower().endswith('.pdf'):
                    # Try native extraction first
                    text = extract_pdf_text_native(file.getvalue())
                    if not text.strip():
                        # If no text, try OCR
                        text = extract_text_from_pdf_with_ocr(file.getvalue())
                else:
                    # Image file - use OCR
                    text = extract_text_from_image(file.getvalue())
                
                if text.strip():
                    # Parse text
                    df = parser.parse_text(text)
                    if not df.empty:
                        df['Fajl'] = file.name
                        all_results.append(df)
                        st.success(f"✅ {file.name}: {len(df)} analita pronađeno")
                    else:
                        st.warning(f"⚠️ {file.name}: Nema analita")
                else:
                    st.error(f"❌ {file.name}: Nije moguće izvući tekst")
        
        # Combine all results
        if all_results:
            final_df = pd.concat(all_results, ignore_index=True)
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Ukupno analita", len(final_df))
            with col2:
                st.metric("Fajlova", len(uploaded_files))
            with col3:
                st.metric("Normalni", len(final_df[final_df['Status'] == 'Normalno']))
            with col4:
                st.metric("Abnormalni", len(final_df[final_df['Status'].isin(['Povišeno', 'Sniženo'])]))

else:  # Text mode
    st.markdown("""
    <div class="upload-section">
        <h3>📝 Unesite tekst laboratorijskog nalaza</h3>
        <p>Zalijepite tekst direktno u polje ispod</p>
    </div>
    """, unsafe_allow_html=True)
    
    text_input = st.text_area("Tekst nalaza:", height=200, placeholder="Zalijepite tekst laboratorijskog nalaza ovde...")
    
    if text_input and st.button("🔍 Analiziraj tekst", type="primary"):
        with st.spinner("Analiziram tekst..."):
            parser = LabResultParser()
            df = parser.parse_text(text_input)
            
            if not df.empty:
                st.success(f"✅ Pronađeno {len(df)} analita")
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Ukupno analita", len(df))
                with col2:
                    st.metric("Normalni", len(df[df['Status'] == 'Normalno']))
                with col3:
                    st.metric("Abnormalni", len(df[df['Status'].isin(['Povišeno', 'Sniženo'])]))

# Display results
if 'final_df' in locals() and not final_df.empty:
    st.markdown("### 📊 Rezultati")
    
    # Display table
    st.dataframe(final_df, use_container_width=True)
    
    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        csv = final_df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            "lab_results.csv",
            "text/csv"
        )
    with col2:
        # Excel download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Lab Results')
        excel_data = output.getvalue()
        
        st.download_button(
            "📥 Download Excel",
            excel_data,
            "lab_results.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif 'df' in locals() and not df.empty:
    st.markdown("### 📊 Rezultati")
    
    # Display table
    st.dataframe(df, use_container_width=True)
    
    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            "lab_results.csv",
            "text/csv"
        )
    with col2:
        # Excel download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Lab Results')
        excel_data = output.getvalue()
        
        st.download_button(
            "📥 Download Excel",
            excel_data,
            "lab_results.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🧪 Lab Reader v4 - Univerzalni parser za laboratorijske nalaze</p>
    <p>Podrška za PDF, slike i OCR funkcionalnost</p>
</div>
""", unsafe_allow_html=True)
