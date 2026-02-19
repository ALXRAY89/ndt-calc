import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="NDT ISO Pro Optimizer", layout="wide")

# --- Справочники ISO 17636-2 ---
def get_iso_limits(w):
    snr_a, snr_b = 70, 130
    if w <= 1.2: return 50, 40, snr_a, snr_b
    if w <= 5.0: return 100, 80, snr_a, snr_b
    if w <= 12: return 130, 100, snr_a, snr_b
    if w <= 40: return 160, 130, snr_a, snr_b
    return 200, 160, snr_a, snr_b

# Режимы: {Материал: (базовое_кВ, шаг_кВ_на_мм, фильтр)}
materials_data = {
    "Алюминий": {"dens": 1.0, "kv_base": 50, "kv_step": 2, "filter": "Без фильтра / 0.5 мм Cu"},
    "Титан": {"dens": 1.7, "kv_base": 70, "kv_step": 4, "filter": "0.5 - 1.0 мм Cu"},
    "Сталь": {"dens": 2.9, "kv_base": 100, "kv_step": 5, "filter": "1.0 - 2.0 мм Cu"},
    "Нерж. сталь": {"dens": 3.0, "kv_base": 110, "kv_step": 5, "filter": "1.5 - 2.0 мм Cu"}
}

st.title("🔬 Продвинутый NDT & Микрофокус Оптимизатор")

# --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
with st.sidebar:
    st.header("💡 Источник")
    src_type = st.radio("Диапазон фокуса", ["Микро (1-100 мкм)", "Макро (0.1-3 мм)"])
    f_mkm = st.slider("Размер фокуса (мкм)", 1, 100, 10) if src_type == "Микро (1-100 мкм)" else st.slider("Размер фокуса (мм)", 0.1, 3.0, 0.4, 0.1) * 1000
    
    st.header("📲 Детектор")
    pixel = st.number_input("Пиксель (мкм)", value=64)
    mtf_k = st.slider("MTF (размытие)", 1.0, 3.0, 1.6)
    srb_det = pixel * mtf_k

    st.header("📐 Геометрия и Объект")
    fdd = st.slider("FDD (мм)", 200, 1000, 600)
    obj_size = st.slider("Габарит образца (мм)", 1, 100, 20)
    wall_w = st.slider("Толщина стенок (мм)", 1, 100, 10)
    material = st.selectbox("Материал", list(materials_data.keys()))

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
res_center = res_axis[idx_min]
res_worst = max(calc_res_target(b_opt + obj_size/2), calc_res_target(b_opt - obj_size/2))
limit_a, limit_b, snr_a, snr_b = get_iso_limits(wall_w)
m_val = fdd / (fdd - b_opt)

# Рекомендуемые параметры трубки
mat_info = materials_data[material]
rec_kv = min(320, mat_info["kv_base"] + (wall_w * mat_info["kv_step"]))
rec_filter = mat_info["filter"] if wall_w > 5 else "Без фильтра"

# --- ИНТЕРФЕЙС ВЫВОДА ---
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Оптим. позиция", f"{b_opt:.1f} мм"); st.caption(f"M = {m_val:.2f}")
with c2: st.metric("SRb (Центр)", f"{res_center:.1f} мкм"); st.write("✅ Класс B" if res_worst <= limit_b else "❌ Вне B")
with c3: st.metric("Реком. энергия", f"{rec_kv:.0f} кВ", help="Ориентировочное напряжение для обеспечения контраста."); st.caption(f"Фильтр: {rec_filter}")
with c4: st.metric("SNR_norm (B)", f"{snr_b}"); st.caption(f"Лимит B: {limit_b} мкм")

# График
fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="SRb на объекте", line=dict(width=4, color='#1f77b4')))
fig.add_vrect(x0=max(0, b_opt-obj_size/2), x1=min(fdd, b_opt+obj_size/2), fillcolor="rgba(255, 127, 14, 0.2)", line_width=0, annotation_text="ОБЪЕКТ")
fig.add_trace(go.Scatter(x=[b_opt], y=[res_center], mode='markers', marker=dict(size=12, color='red', symbol='diamond'), name="Оптимум"))
fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Лимит B")
st.plotly_chart(fig, use_container_width=True)

# --- ТЕКСТОВЫЙ ПРОТОКОЛ ---
st.divider()
st.subheader("📋 Протокол рекомендуемых параметров")

report_text = f"""ПРОТОКОЛ РАСЧЕТА NDT (ISO 17636-2)
--------------------------------------
ОБЪЕКТ: {material}, суммарная толщина {wall_w} мм
СИСТЕМА: Фокус {f_mkm} мкм, Детектор {srb_det:.1f} мкм (эфф.)
--------------------------------------
РЕКОМЕНДУЕМАЯ ГЕОМЕТРИЯ:
- Дистанция FDD: {fdd} мм
- Позиция центра объекта (b): {b_opt:.1f} мм от детектора
- Увеличение (M): {m_val:.2f}
--------------------------------------
РЕКОМЕНДУЕМЫЕ ПАРАМЕТРЫ ИСТОЧНИКА:
- Напряжение на трубке: ~{rec_kv:.0f} кВ
- Внешний фильтр: {rec_filter}
--------------------------------------
ТРЕБОВАНИЯ СТАНДАРТА (Класс B):
- Макс. нерезкость (SRb): {limit_b} мкм
- Мин. сигнал/шум (SNR_norm): {snr_b}
--------------------------------------
ПРОГНОЗ РЕЗУЛЬТАТА:
- SRb (наихудшее в объеме): {res_worst:.1f} мкм
- СТАТУС ПО РАЗРЕШЕНИЮ: {"✅ СООТВЕТСТВУЕТ" if res_worst <= limit_b else "❌ НЕ СООТВЕТСТВУЕТ"}
--------------------------------------"""

st.code(report_text, language="text")
