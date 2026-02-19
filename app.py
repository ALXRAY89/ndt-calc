import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Advanced NDT Designer", layout="wide")

# --- ЛОГИКА ISO 17636-2 ---
def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

st.title("🔬 Advanced NDT & Microfocus Designer")

# --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
with st.sidebar:
    st.header("💡 Источник излучения")
    src_type = st.radio("Тип источника", ["Микрофокус (5-100 мкм)", "Обычный (0.1-3 мм)"])
    
    if src_type == "Микрофокус (5-100 мкм)":
        f_val = st.slider("Размер фокуса (мкм)", 5, 100, 20)
        f_mm = f_val / 1000
    else:
        f_mm = st.slider("Размер фокуса (мм)", 0.1, 3.0, 0.4, 0.1)
    
    f_input = st.number_input("Точный ввод фокуса (мм)", value=float(f_mm), format="%.3f")
    f_final = f_input # Используем прямое поле ввода как приоритет

    st.header("📲 Детектор (MTF)")
    pixel_size = st.number_input("Размер пикселя (мкм)", value=64)
    # MTF10% обычно соответствует 1.4-2.0 пикселя в зависимости от сцинтиллятора
    mtf_factor = st.slider("MTF 10% (в пикселях)", 1.0, 3.0, 1.6, 0.1, 
                           help="Обычно 1.6 для CsI и 2.0+ для Gadox")
    effective_srb = pixel_size * mtf_factor

    st.header("📐 Геометрия и Объект")
    fdd = st.number_input("Расстояние FDD (мм)", value=600)
    obj_depth = st.number_input("Габарит (глубина) образца (мм)", value=20)
    total_w = st.number_input("Общая толщина материала (мм)", value=10)

# --- МАТЕМАТИКА ОПТИМИЗАЦИИ ---
# Ищем оптимальное положение (M_opt), где Ug = Up
# f * (M-1) = SRb_det / M  => M^2 - M - (SRb_det/f) = 0
f_mkm = f_final * 1000
m_opt = (1 + np.sqrt(1 + 4 * (effective_srb / f_mkm))) / 2
b_opt = fdd * (1 - 1/m_opt)

# Расчет нерезкости для текущего диапазона внутри объекта
b_front = b_opt + (obj_depth / 2) # дальняя точка от детектора
b_back = b_opt - (obj_depth / 2)  # ближняя точка к детектору

def calc_res(dist):
    a = fdd - dist
    if a <= 0: return 999
    ug = f_mkm * (dist / a)
    up = effective_srb / (fdd / a)
    return np.sqrt(ug**2 + up**2)

res_front = calc_res(b_front)
res_back = calc_res(b_back)
limit_a, limit_b = get_iso_limits(total_w)

# --- ИНТЕРФЕЙС ВЫВОДА ---
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Оптим. позиция (от детектора)", f"{b_opt:.1f} мм")
    st.caption(f"Оптимальное увеличение M = {m_opt:.2f}")
with c2:
    st.metric("Разрешение в объеме", f"{res_front:.1f} — {res_back:.1f} мкм")
    status = "✅ OK (Класс B)" if res_front <= limit_b else "⚠️ Вне Класса B"
    st.write(status)
with c3:
    st.metric("Эффект. пиксель детектора", f"{effective_srb:.1f} мкм")
    st.caption("С учетом MTF размытия")

# --- ГРАФИК ---
b_axis = np.linspace(0.1, fdd*0.8, 500)
res_axis = [calc_res(x) for x in b_axis]

fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="Профиль разрешения", line=dict(width=3, color='RoyalBlue')))

# Подсветка габаритов образца
fig.add_vrect(x0=max(0, b_back), x1=min(fdd, b_front), 
              fillcolor="orange", opacity=0.2, layer="below", line_width=0,
              annotation_text="Объем образца")

fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Лимит ISO Класс B")

fig.update_layout(
    xaxis_title="Расстояние от детектора (мм)",
    yaxis_title="Разрешение SRb (мкм)",
    yaxis_range=[0, max(res_axis)*0.5 if max(res_axis)>200 else 200],
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

st.info(f"**Анализ:** Для достижения наилучшего разрешения по всему объему ({obj_depth} мм), "
        f"центр образца должен находиться в {b_opt:.1f} мм от детектора. "
        f"Наихудшее разрешение будет на передней стенке: {res_front:.1f} мкм.")
