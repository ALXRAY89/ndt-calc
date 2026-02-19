import streamlit as st
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF # Используйте библиотеку fpdf2 (pip install fpdf2)

st.set_page_config(page_title="NDT ISO Pro Expert", layout="wide")

# --- Справочники ---
def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

materials = {"Aluminium": 1.0, "Titanium": 1.7, "Steel": 2.9, "Stainless Steel": 3.0}

st.title("🔬 Advanced NDT & Microfocus Optimizer v10")

# --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
with st.sidebar:
    st.header("💡 Source")
    src_type = st.radio("Focus Range", ["Micro (1-100 um)", "Macro (0.1-3 mm)"])
    f_mkm = st.slider("Focus size (um)", 1, 100, 10) if src_type == "Micro (1-100 um)" else st.slider("Focus size (mm)", 0.1, 3.0, 0.4, 0.1) * 1000
    
    st.header("📲 Detector")
    pixel = st.number_input("Pixel size (um)", value=64)
    mtf_k = st.slider("MTF factor", 1.0, 3.0, 1.6)
    srb_det = pixel * mtf_k

    st.header("📐 Geometry & Object")
    fdd = st.slider("FDD (mm)", 200, 1000, 600)
    obj_size = st.slider("Object size (mm)", 1, 100, 20)
    wall_w = st.slider("Wall thickness (mm)", 1, 100, 10)
    material = st.selectbox("Material", list(materials.keys()))

# --- МАТЕМАТИКА ---
def calc_res_target(b_dist):
    a = fdd - b_dist
    if a <= 0.5: return f_mkm
    m = fdd / a
    return np.sqrt((f_mkm * (b_dist / fdd))**2 + (srb_det / m)**2)

b_axis = np.linspace(0, fdd * 0.98, 1000)
res_axis = [calc_res_target(x) for x in b_axis]
idx_min = np.argmin(res_axis)
b_opt = b_axis[idx_min]
m_val = fdd / (fdd - b_opt)
res_center = res_axis[idx_min]
res_worst = max(calc_res_target(b_opt + obj_size/2), calc_res_target(b_opt - obj_size/2))
limit_a, limit_b = get_iso_limits(wall_w)

# --- ИНТЕРФЕЙС ---
c1, c2, c3 = st.columns(3)
with c1: st.metric("Opt. Position b", f"{b_opt:.1f} mm"); st.caption(f"Mag M = {m_val:.2f}")
with c2: st.metric("SRb (Center)", f"{res_center:.1f} um"); st.write("✅ Class B" if res_worst <= limit_b else "❌ Fail")
with c3: st.metric("SRb (Worst)", f"{res_worst:.1f} um"); st.caption(f"Limit B: {limit_b} um")

# График
fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="Target SRb", line=dict(width=3)))
fig.add_vrect(x0=max(0, b_opt-obj_size/2), x1=min(fdd, b_opt+obj_size/2), fillcolor="orange", opacity=0.2, annotation_text="OBJECT")
st.plotly_chart(fig, use_container_width=True)

# --- ГЕНЕРАЦИЯ PDF (БЕЗ РУССКИХ БУКВ ДЛЯ ИСКЛЮЧЕНИЯ ОШИБОК КОДИРОВКИ) ---
def create_pdf_bytes():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "NDT INSPECTION PROTOCOL (ISO 17636-2)", ln=True, align='C')
    pdf.set_font("helvetica", size=12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Material: {material} | Thickness: {wall_w} mm", ln=True)
    pdf.cell(0, 10, f"Focus: {f_mkm} um | Pixel: {pixel} um | MTF: {mtf_k}", ln=True)
    pdf.cell(0, 10, f"FDD: {fdd} mm | Opt. Position b: {b_opt:.1f} mm", ln=True)
    pdf.cell(0, 10, f"Magnification M: {m_val:.2f}", ln=True)
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, f"Result SRb (Center): {res_center:.1f} um", ln=True)
    pdf.set_font("helvetica", size=12)
    pdf.multi_cell(0, 10, f"JUSTIFICATION: Object is placed at the resolution minimum where geometric blur and detector resolution are balanced. Safety margin to Class B limit ({limit_b} um): {((limit_b - res_worst)/limit_b * 100):.1f}%.")
    return pdf.output() # fpdf2 по умолчанию возвращает bytearray

if st.button("📥 Export Protocol to PDF"):
    try:
        pdf_bytes = create_pdf_bytes()
        st.download_button(
            label="Click here to download PDF",
            data=bytes(pdf_bytes),
            file_name="ndt_protocol.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
