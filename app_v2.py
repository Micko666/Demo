import io
import re
import pandas as pd
import streamlit as st

# ---------------- UI ----------------
st.set_page_config(page_title="Čitač nalaza – v37 (auto + ciljani)", page_icon="🧪", layout="wide")
st.title("🧪 Čitač laboratorijskih nalaza – v37")
st.caption("Auto parser + ciljani režim (riječnik analita). Radi na tekstualnim PDF-ovima.")

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Podešavanja")
    layout_opt = st.radio("Raspored tabele", ["Široko", "Centar"], index=0)
    show_preview = st.checkbox("Prikaži preview teksta", value=True)
    st.markdown("---")
    st.subheader("Unos")
    upload_mode = st.radio("Izvor podataka", ["PDF", "Tekst (paste)"]) 
    st.caption("Možeš učitati više PDF-ova odjednom ili zalijepiti tekst nalaza.")
    folder_path = ""
    if upload_mode == "PDF":
        folder_path = st.text_input("📁 Folder sa PDF-ovima (opciono)", "")
        st.caption("Ako uneseš folder, svi .pdf fajlovi u njemu biće učitani.")

with st.expander("ℹ️ Kako radi"):
    st.markdown("""
**Dva koraka:**
1) **Auto režim**: pretražuje cijeli tekst i pokušava prepoznati *Analit + Vrijednost + Jedinica + Referentni opseg* bez pretpostavki o formatu.
2) **Ciljani režim**: za unaprijed definisane analite (npr. Hemoglobin, Leukociti, Glukoza...) posebno traži vrijednost, jedinicu i referentne vrijednosti u blizini naziva, čak i ako su u sljedećoj liniji.

Možeš proširiti listu analita u kodu (ANALYTE_CATALOG). OCR nije uključen (potreban je tekstualni PDF).
""")

uploaded_files = None
text_input_fallback = None
if 'upload_mode' in locals() and upload_mode == "Tekst (paste)":
    text_input_fallback = st.text_area("📋 Zalijepi tekst nalaza", "", height=200)
else:
    uploaded_files = st.file_uploader("📤 Učitaj PDF nalaza (više datoteka dozvoljeno)", type=["pdf"], accept_multiple_files=True)

if layout_opt == "Centar":
    st.write("")  # zadrži centrirani osjećaj minimalnom promjenom

# ---------------- PDF text (bez OCR) ----------------
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

# ---------------- Helpers ----------------
def d2f(s: str):
    try:
        return float(s.replace(",", "."))
    except:
        return None

NUM   = r"[-+]?\d+(?:[.,]\d+)?"
QUAL  = r"(?:Negativan|Normalan|Pozitivan)"
RANGE = rf"(?:{NUM}\s*[~\-]\s*{NUM}|<\s*{NUM}|>\s*{NUM}|{QUAL})"
UNIT  = r"(?:10[\*\^]\d+\/[A-Za-z]+|[A-Za-z%\/\*\.\-\^]+)"

def normalize_units(u: str) -> str:
    if not u:
        return ""
    u = u.replace("^", "*")
    u = u.replace("µ", "u")
    return re.sub(r"\s+", "", u)

UNIT_TAIL = re.compile(
    r"(?:"
    r"(?:10[\*\^]\d+\/[A-Za-z]+)"
    r"|(?:[fpnumk]?g\/L|ng\/mL|ug\/mL|mg\/dL|mmol\/L|mol\/L|U\/L|IU\/L|mIU\/L)"
    r"|(?:L\/L)"
    r"|(?:fL|pL|nL|pg)"
    r"|(?:%)"
    r")\s*$",
    re.IGNORECASE
)

def clean_name_and_type(name: str, unit_guess: str):
    name = (name or "").strip()
    if name.lower().startswith(("k-", "s-")):
        name = name[2:].strip()
    name = re.sub(r"\s+", " ", name.replace("aps.", "aps")).strip()
    typ = ""
    if name.endswith("%"):
        typ = "%"
        name = name[:-1].strip()
    if name.lower().endswith(" aps"):
        typ = "aps"
        name = name[:-3].strip()
    while UNIT_TAIL.search(name):
        name = UNIT_TAIL.sub("", name).strip()
    if not typ and (unit_guess or "").strip() == "%":
        typ = "%"
    
    # Čišćenje kvalitativnih rezultata
    if unit_guess and unit_guess.lower() in ["negativan", "normalan", "pozitivan"]:
        unit_guess = ""
    
    return name, typ

def status_from(v_num, ref_low, ref_high, ref_type, v_qual=None, qual_ref=None):
    if v_num is not None:
        if ref_type == "range" and ref_low is not None and ref_high is not None:
            if v_num < ref_low: return "⬇️ ispod"
            if v_num > ref_high: return "⬆️ iznad"
            return "✅ u referentnom"
        if ref_type == "<" and ref_high is not None:
            return "✅ u referentnom" if v_num < ref_high else "⬆️ iznad"
        if ref_type == ">" and ref_low is not None:
            return "✅ u referentnom" if v_num > ref_low else "⬇️ ispod"
        return ""
    if v_qual is not None and qual_ref is not None:
        return "✅ u referentnom" if v_qual == qual_ref else "⚠️ odstupanje"
    return ""

# ---------------- UNIVERZALNI PARSER ----------------
# Poboljšani patterni koji rade sa različitim formatima
PAT_UNIVERSAL = re.compile(
    rf"(?P<an>[A-Za-zČĆŠĐŽčćšđž][A-Za-zČĆŠĐŽčćšđž\s\.\-%]+?)\s+(?P<val>{NUM}|{QUAL})\s+(?P<un>{UNIT})?\s*(?P<ref>{RANGE})?"
)

# Pattern za državni sistem (format: Analit Vrijednost Jedinica Ref)
PAT_STATE = re.compile(
    rf"^(?P<an>[A-Za-zČĆŠĐŽčćšđž][A-Za-zČĆŠĐŽčćšđž\s\.\-%]+?)\s+(?P<val>{NUM}|{QUAL})\s+(?P<un>{UNIT})?\s*(?P<ref>{RANGE})?\s*$"
)

# Pattern za tablični format (kolone razdvojene sa 2+ razmaka)
PAT_TABLE = re.compile(
    rf"(?P<an>[A-Za-zČĆŠĐŽčćšđž][A-Za-zČĆŠĐŽčćšđž\s\.\-%]+?)\s{{2,}}(?P<val>{NUM}|{QUAL})\s+(?P<un>{UNIT})?\s*(?P<ref>{RANGE})?"
)

# Stari patterni za kompatibilnost
PAT_A = re.compile(  # Ime → [H/L]? → Vrijednost → (Jedinica) → Ref
    rf"(?P<an>[A-Za-zČĆŠĐŽčćšđž\.\-% ]+?)\s+(?P<fl>[HL])?\s*(?P<val>{NUM}|{QUAL})\s+(?P<un>{UNIT})?\s*(?P<ref>{RANGE})"
)
PAT_B = re.compile(  # [H/L]? → Vrijednost → (Jedinica) → Ref → Ime
    rf"(?P<fl>[HL])?\s*(?P<val>{NUM}|{QUAL})\s+(?P<un>{UNIT})?\s*(?P<ref>{RANGE})\s+(?P<an>[A-Za-zČĆŠĐŽčćšđž\.\-% ]+)"
)
PAT_C = re.compile(  # Ime → Vrijednost → Jedinica (bez ref)
    rf"(?P<an>[A-Za-zČĆŠĐŽčćšđž\.\-% ]+?)\s+(?P<val>{NUM})\s+(?P<un>{UNIT})\b"
)
PAT_D = re.compile(  # Vrijednost → Jedinica → Ime (bez ref)
    rf"(?P<val>{NUM})\s+(?P<un>{UNIT})\s+(?P<an>[A-Za-zČĆŠĐŽčćšđž\.\-% ]+)"
)
PAT_MOJLAB = re.compile(  # Specifično: val unit ref_low - ref_high K-Analit
    rf"(?P<val>{NUM})\s+(?P<un>{UNIT})\s*(?P<low>{NUM})\s*-\s*(?P<high>{NUM})\s*(?P<an>K-[A-Za-zČĆŠĐŽčćšđž\.\-% ]+)$"
)

# Lista poznatih analita za validaciju
KNOWN_ANALYTES = {
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

# Lista reči koje treba da se preskoče
SKIP_WORDS = {
    "laboratorijska", "dijagnostika", "uzorkovanja", "vrijeme", "datum", "pacijent", 
    "doktor", "dr", "serum", "plazma", "citrat", "punkt", "protokola", "br.",
    "aligrudić", "golubovci", "filip", "mara", "džomić", "qo", "med", "dijag",
    "normalan", "negativan", "pozitivan", "granulociti", "epitelne", "cel",
    "neskvamozne", "bubrežni", "epitel", "elije", "težina", "specifina"
}

def is_valid_analyte(name: str) -> bool:
    """Proverava da li je naziv valjan analit"""
    if not name or len(name.strip()) < 2:
        return False
    
    name_lower = name.lower().strip()
    
    # Preskoči ako sadrži skip reči
    for skip_word in SKIP_WORDS:
        if skip_word in name_lower:
            return False
    
    # Proveri da li sadrži poznate analite
    for analyte in KNOWN_ANALYTES:
        if analyte in name_lower:
            return True
    
    # Proveri da li je kratak i smislen (1-3 reči)
    words = name_lower.split()
    if len(words) <= 3 and all(len(w) > 1 for w in words):
        # Dodatna provera - ne sme biti samo brojevi ili kratke reči
        if not all(w.isdigit() or len(w) < 3 for w in words):
            return True
    
    return False

def interpret_auto_match(name_raw, val_raw, unit_raw, ref_raw, flag_raw, line):
    name, typ = clean_name_and_type(name_raw, unit_raw or "")
    unit = normalize_units(unit_raw or "")
    # value
    v_num = d2f(val_raw) if re.fullmatch(NUM, val_raw or "") else None
    v_qual = val_raw if v_num is None and val_raw else None
    
    # Skip if no meaningful analyte name or invalid analyte
    if not name or len(name.strip()) < 2 or not is_valid_analyte(name):
        return None
    
    # ref
    ref_low = ref_high = None
    ref_type = "none"
    qual_ref = None
    if ref_raw:
        ref_raw = ref_raw.strip()
        if re.match(rf"^{NUM}\s*[~\-]\s*{NUM}$", ref_raw):
            a,b = re.split(r"[~\-]", ref_raw)
            ref_low, ref_high = d2f(a.strip()), d2f(b.strip()); ref_type = "range"
        elif re.match(rf"^<\s*{NUM}$", ref_raw):
            ref_high = d2f(ref_raw.split("<")[1].strip()); ref_type = "<"
        elif re.match(rf"^>\s*{NUM}$", ref_raw):
            ref_low = d2f(ref_raw.split(">")[1].strip()); ref_type = ">"
        elif re.fullmatch(QUAL, ref_raw):
            qual_ref = ref_raw; ref_type = "qual"
    status = status_from(v_num, ref_low, ref_high, ref_type, v_qual, qual_ref)
    return {
        "Analit": name, "Tip": typ,
        "Vrijednost": v_num if v_num is not None else v_qual,
        "Jedinica": unit,
        "Ref_low": ref_low, "Ref_high": ref_high, "Ref_tip": ref_type, "Ref_kval": qual_ref,
        "Flag": (flag_raw or "").strip(),
        "Status": status,
        "Izvor": "auto",
        "Linija": line
    }

def auto_parse(text: str) -> pd.DataFrame:
    lines = []
    for ln in text.splitlines():
        s = " ".join(ln.split())
        if not s: continue
        parts = re.split(r"\s{3,}|\t+", s)  # dvokolonski split
        if len(parts) > 1: lines.extend([p.strip() for p in parts if p.strip()])
        else: lines.append(s)

    rows = []
    for line in lines:
        # MojLab specifično
        m = PAT_MOJLAB.search(line)
        if m:
            g = m.groupdict()
            result = interpret_auto_match(g["an"], g["val"], g["un"], f"{g['low']}-{g['high']}", "", line)
            if result:
                rows.append(result)

        # Novi univerzalni patterni (prioritet)
        for m in PAT_UNIVERSAL.finditer(line):
            g = m.groupdict()
            result = interpret_auto_match(g["an"], g["val"], g.get("un"), g.get("ref"), "", line)
            if result:
                rows.append(result)
        
        for m in PAT_STATE.finditer(line):
            g = m.groupdict()
            result = interpret_auto_match(g["an"], g["val"], g.get("un"), g.get("ref"), "", line)
            if result:
                rows.append(result)
        
        for m in PAT_TABLE.finditer(line):
            g = m.groupdict()
            result = interpret_auto_match(g["an"], g["val"], g.get("un"), g.get("ref"), "", line)
            if result:
                rows.append(result)

        # Stari patterni (fallback)
        for m in PAT_A.finditer(line):
            g = m.groupdict()
            result = interpret_auto_match(g["an"], g["val"], g.get("un"), g.get("ref"), g.get("fl"), line)
            if result:
                rows.append(result)
        for m in PAT_B.finditer(line):
            g = m.groupdict()
            result = interpret_auto_match(g["an"], g["val"], g.get("un"), g.get("ref"), g.get("fl"), line)
            if result:
                rows.append(result)
        for m in PAT_C.finditer(line):
            g = m.groupdict()
            result = interpret_auto_match(g["an"], g["val"], g.get("un"), "", "", line)
            if result:
                rows.append(result)
        for m in PAT_D.finditer(line):
            g = m.groupdict()
            result = interpret_auto_match(g["an"], g["val"], g.get("un"), "", "", line)
            if result:
                rows.append(result)

    if not rows:
        return pd.DataFrame(columns=["Analit","Tip","Vrijednost","Jedinica","Ref_low","Ref_high","Ref_tip","Ref_kval","Flag","Status","Izvor","Linija"])
    df = pd.DataFrame(rows)
    
    # Poboljšana deduplikacija - prioritet ciljanom parseru
    df["_priority"] = df["Izvor"].map({"ciljani": 1, "auto": 2})
    df = df.sort_values(["_priority", "Ref_low", "Ref_high"], na_position="last")
    df = df.drop_duplicates(subset=["Analit", "Tip"], keep="first")
    df = df.drop(columns=["_priority"])
    
    return df

# ---------------- CILJANI PARSER (riječnik) ----------------
# Sinonimi po laboratorijama/jezičkim varijantama; slobodno proširi
ANALYTE_CATALOG = [
    {"name": "Hemoglobin",      "aliases": ["Hemoglobin","Hb"]},
    {"name": "Leukociti",       "aliases": ["Leukociti","Leukocite","WBC"]},
    {"name": "Eritrociti",      "aliases": ["Eritrociti","Eritrocite","RBC","K-Eritrociti"]},
    {"name": "Hematokrit",      "aliases": ["Hematokrit","HCT"]},
    {"name": "Trombociti",      "aliases": ["Trombociti","PLT"]},
    {"name": "Glukoza",         "aliases": ["Glukoza","Glucose"]},
    {"name": "Urea",            "aliases": ["Urea"]},
    {"name": "Kreatinin",       "aliases": ["Kreatinin","Creatinine"]},
    {"name": "ALT",             "aliases": ["ALT","GPT"]},
    {"name": "AST",             "aliases": ["AST","GOT"]},
    {"name": "GGT",             "aliases": ["GGT","Gamma GT","Gamma-GT"]},
    {"name": "Ukupni holesterol","aliases": ["Ukupni holesterol","Holesterol ukupni","Cholesterol total"]},
    {"name": "HDL",             "aliases": ["HDL"]},
    {"name": "LDL",             "aliases": ["LDL"]},
    {"name": "Trigliceridi",    "aliases": ["Trigliceridi","Triglycerides","Trigl."]},
    {"name": "Natrijum",        "aliases": ["Natrijum","Na"]},
    {"name": "Kalijum",         "aliases": ["Kalijum","K"]},
    {"name": "Kalcijum",        "aliases": ["Kalcijum","Ca"]},
    {"name": "Neutrofili %",    "aliases": ["Neutrofili %","Neutrofili%","Neutrofili procenat","Neutrophils %"]},
    {"name": "Neutrofili aps",  "aliases": ["Neutrofili aps","Neutrofili aps.","Neutrofili abs","Neutrophils abs"]},
    {"name": "Limfociti %",     "aliases": ["Limfociti %","Lymphocytes %","Limfociti%"]},
    {"name": "Limfociti aps",   "aliases": ["Limfociti aps","Lymphocytes abs","Limfociti aps."]},
    {"name": "Monociti %",      "aliases": ["Monociti %","Monocytes %","Monociti%"]},
    {"name": "Monociti aps",    "aliases": ["Monociti aps","Monocytes abs","Monociti aps."]},
]

# Omogući dodavanje custom analita iz UI (sidebar)
extra_analytes_raw = st.sidebar.text_input("➕ Dodaj analite (zarezom)", "")
if extra_analytes_raw.strip():
    extra_names = [a.strip() for a in extra_analytes_raw.split(",") if a.strip()]
    for n in extra_names:
        ANALYTE_CATALOG.append({"name": n, "aliases": [n]})

# oko svakog “pogođenog” naziva gledamo susjedni prozor teksta i tražimo broj + (jedinicu) + (referencu)
WINDOW_CHARS = 120  # koliko znakova lijevo/desno od naziva gledamo

VAL_PAT   = re.compile(rf"(?P<val>{NUM}|{QUAL})")
UNIT_PAT  = re.compile(rf"(?P<un>{UNIT})")
RANGE_PAT = re.compile(rf"(?P<ref>{RANGE})")

def targeted_parse(text: str) -> pd.DataFrame:
    t_low = text.lower()
    rows = []
    for item in ANALYTE_CATALOG:
        name = item["name"]
        aliases = item["aliases"]
        # napravi regex koji hvata bilo koji alias kao cjelinu (case-insensitive)
        alias_pat = re.compile(r"|".join([re.escape(a) for a in aliases]), re.IGNORECASE)
        for m in alias_pat.finditer(text):
            start, end = m.start(), m.end()
            window_start = max(0, start - WINDOW_CHARS)
            window_end   = min(len(text), end + WINDOW_CHARS)
            window = text[window_start:window_end]

            # U prozoru: prvo vrijednost, pa pokušaj jedinicu i referencu
            val_m   = None
            unit_m  = None
            range_m = None

            # Prioritet: prvo potraži broj/qual oko “desno” od naziva (češći raspored)
            right = text[end: min(len(text), end + WINDOW_CHARS)]
            left  = text[max(0, start - WINDOW_CHARS): start]

            for side in (right, left, window):  # probaj desno, pa lijevo, pa cijeli prozor
                if not val_m:
                    val_m = VAL_PAT.search(side)
                if not unit_m:
                    unit_m = UNIT_PAT.search(side)
                if not range_m:
                    range_m = RANGE_PAT.search(side)

            val_raw  = val_m.group("val") if val_m else ""
            unit_raw = unit_m.group("un") if unit_m else ""
            ref_raw  = range_m.group("ref") if range_m else ""

            # interpretiraj
            clean_name, typ = clean_name_and_type(name, unit_raw or "")
            unit = normalize_units(unit_raw or "")
            v_num = d2f(val_raw) if re.fullmatch(NUM, val_raw or "") else None
            v_qual = val_raw if v_num is None and val_raw else None

            ref_low = ref_high = None
            ref_type = "none"
            qual_ref = None
            if ref_raw:
                ref_raw = ref_raw.strip()
                if re.match(rf"^{NUM}\s*[~\-]\s*{NUM}$", ref_raw):
                    a,b = re.split(r"[~\-]", ref_raw)
                    ref_low, ref_high = d2f(a.strip()), d2f(b.strip()); ref_type="range"
                elif re.match(rf"^<\s*{NUM}$", ref_raw):
                    ref_high = d2f(ref_raw.split("<")[1].strip()); ref_type="<"
                elif re.match(rf"^>\s*{NUM}$", ref_raw):
                    ref_low = d2f(ref_raw.split(">")[1].strip()); ref_type=">"
                elif re.fullmatch(QUAL, ref_raw):
                    qual_ref = ref_raw; ref_type="qual"

            stat = status_from(v_num, ref_low, ref_high, ref_type, v_qual, qual_ref)

            # Only add if we have a meaningful result
            if clean_name and (v_num is not None or v_qual):
                rows.append({
                    "Analit": clean_name, "Tip": typ,
                    "Vrijednost": v_num if v_num is not None else v_qual,
                    "Jedinica": unit,
                    "Ref_low": ref_low, "Ref_high": ref_high, "Ref_tip": ref_type, "Ref_kval": qual_ref,
                    "Flag": "",
                    "Status": stat,
                    "Izvor": "ciljani",
                    "Linija": text[start: end]  # highlight naziva
                })

    if not rows:
        return pd.DataFrame(columns=["Analit","Tip","Vrijednost","Jedinica","Ref_low","Ref_high","Ref_tip","Ref_kval","Flag","Status","Izvor","Linija"])
    df = pd.DataFrame(rows)

    # Ako isti analit dobijemo više puta, zadrži najinformativniji (onaj koji ima i ref)
    df["_info_score"] = df[["Ref_low","Ref_high","Ref_tip"]].notna().sum(axis=1)
    df = df.sort_values(["Analit","_info_score"], ascending=[True, False]).drop_duplicates(subset=["Analit"], keep="first")
    df = df.drop(columns=["_info_score"])
    return df

# ---------------- Keširanje i spoj logika ----------------
@st.cache_data(show_spinner=False)
def _hash_bytes_to_text(b: bytes) -> str:
    import hashlib
    return hashlib.md5(b or b"\x00").hexdigest()

@st.cache_data(show_spinner=False)
def cached_extract_text(byte_digest: str, file_bytes: bytes) -> str:
    return extract_pdf_text_native(file_bytes)

@st.cache_data(show_spinner=False)
def cached_parse_text(text_hash: str, text: str) -> pd.DataFrame:
    """Cache parsed results for faster reruns"""
    return merge_auto_target(text)

def merge_auto_target(text: str) -> pd.DataFrame:
    df_auto = auto_parse(text)
    df_target = targeted_parse(text)
    if not df_auto.empty and not df_target.empty:
        key_cols = ["Analit","Tip"]
        df = pd.concat([
            df_target,
            df_auto[~df_auto.set_index(key_cols).index.isin(df_target.set_index(key_cols).index)]
        ], ignore_index=True)
    elif not df_target.empty:
        df = df_target
    else:
        df = df_auto
    return df

# ---------------- MAIN ----------------
dataframes = []
if upload_mode == "Tekst (paste)":
    if (text_input_fallback or "").strip():
        text = text_input_fallback
        if show_preview:
            st.text_area("📄 Tekst iz nalaza (preview)", text, height=230)
        
        # Cache parsed results
        text_hash = _hash_bytes_to_text(text.encode())
        df = cached_parse_text(text_hash, text)
        
        if not df.empty:
            dataframes.append(df)
        else:
            st.warning("⚠️ Nije prepoznat nijedan red iz zalijepljenog teksta.")
    else:
        st.info("📋 Zalijepi tekst nalaza u polje sa lijeve strane.")
else:
    if uploaded_files or (folder_path or "").strip():
        # Pripremi zajedničku listu fajlova (upload + folder)
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
            for p in sorted(glob.glob(os.path.join(folder_path, "*.pdf"))):
                selected_files.append(_LocalFile(p))

        for f in selected_files:
            by = f.read()
            with st.spinner(f"⏳ Čitam {f.name}..."):
                digest = _hash_bytes_to_text(by)
                text = cached_extract_text(digest, by)
            if not text.strip():
                st.error(f"❌ {f.name}: Nema tekst (vjerovatno sken/slika). Ova verzija radi bez OCR-a.")
                continue
            if show_preview:
                with st.expander(f"📄 Tekst: {f.name}"):
                    st.text_area("", text, height=200)
            
            # Cache parsed results
            text_hash = _hash_bytes_to_text(text.encode())
            df = cached_parse_text(text_hash, text)
            
            if not df.empty:
                dataframes.append(df)
            else:
                st.warning(f"⚠️ {f.name}: Nije prepoznat nijedan red.")
    else:
        st.info("📂 Učitaj jedan ili više tekstualnih PDF-ova ili pređi na 'Tekst (paste)'.")

if dataframes:
    combined = pd.concat(dataframes, ignore_index=True)
    view_cols = ["Analit","Tip","Vrijednost","Jedinica","Ref_low","Ref_high","Ref_tip","Status","Izvor"]
    st.subheader("📊 Izvučeni podaci (spoj auto + ciljani)")
    st.dataframe(combined[view_cols], use_container_width=True)

    st.markdown("**Filtriraj odstupanja:**")
    only_out = st.checkbox("Prikaži samo van referentnog", value=False)
    filt = combined[combined["Status"].str.contains("⬆️|⬇️|⚠️", na=False)] if only_out else combined
    st.dataframe(filt[view_cols], use_container_width=True)

    # Kratki sažetak i graf
    st.markdown("---")
    st.subheader("📈 Sažetak statusa")
    counts = combined["Status"].fillna("").replace({"": "Bez statusa"}).value_counts()
    st.bar_chart(counts)

    # Preuzimanja
    st.subheader("⬇️ Preuzimanja")
    csv_bytes = combined.to_csv(index=False).encode("utf-8")
    st.download_button("Preuzmi COMBINED CSV", data=csv_bytes, file_name="lab_extract_v37_combined.csv", mime="text/csv")
    import io as _io
    out = _io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as w:
        combined.to_excel(w, index=False, sheet_name="Nalazi")
    st.download_button("Preuzmi COMBINED Excel", data=out.getvalue(),
                       file_name="lab_extract_v37_combined.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Per-file export dugmad (samo ako ima više fajlova)
    if len(dataframes) > 1:
        with st.expander("Per-file export"):
            for i, dfi in enumerate(dataframes):
                c_bytes = dfi.to_csv(index=False).encode("utf-8")
                fname = f"file_{i+1}"
                st.download_button(f"CSV – {fname}", data=c_bytes, file_name=f"lab_extract_{fname}_v37.csv", mime="text/csv")
        
else:
    pass

# ---------------- CLI batch mode ----------------
def _run_cli_if_needed():
    import sys, os, glob
    args = sys.argv[1:]
    if not args:
        return
    if args and args[0] == "--cli":
        # Usage: python app_v2.py --cli <input_folder> <output_csv>
        in_dir = args[1] if len(args) > 1 else os.getcwd()
        out_csv = args[2] if len(args) > 2 else os.path.join(in_dir, "lab_extract_combined.csv")
        frames = []
        for p in sorted(glob.glob(os.path.join(in_dir, "*.pdf"))):
            with open(p, "rb") as fh:
                by = fh.read()
            digest = _hash_bytes_to_text(by)
            text = cached_extract_text(digest, by)
            if not text.strip():
                continue
            df = merge_auto_target(text)
            if not df.empty:
                frames.append(df)
        if frames:
            combined_cli = pd.concat(frames, ignore_index=True)
            combined_cli.to_csv(out_csv, index=False)
            print(f"Saved: {out_csv}")
        else:
            print("No results parsed.")

_run_cli_if_needed()
