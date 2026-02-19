import streamlit as st
import numpy as np
import plotly.graph_objects as go
import urllib.parse

st.set_page_config(page_title="NDT ISO Pro Expert", layout="wide")

# --- Справочники ---
def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

materials = {"Алюминий": 1.0, "Титан": 1.7, "Сталь": 2.9, "Нерж. сталь": 3.0}
mat_list = list(materials.keys())

# --- ЧТЕНИЕ URL ПАРАМЕТРОВ ---
query_params = st.query_params

# Функция для безопасного получения параметров из URL
def get_param(key, default, is_int=True):
    val = query_params.get(key, default)
    return int(val) if is_int else val

# --- ПАНЕЛЬ УПРАВЛЕНИЯ (С ПОДДЕРЖКОЙ URL) ---
with st.sidebar:
    st.header("💡 Источник")
    # Восстанавливаем состояние из URL или ставим дефолт
    src_type_idx = 0 if query_params.get("type") == "micro" else 1
    src_type = st.radio("Диапазон фокуса", ["Микро (1-100 мкм)", "Макро (0.1-3 мм)"], index=src_type_idx)
    
    f_def = get_param("f", 10 if src_type_idx == 0 else 4)
    if src_type == "Микро (1-100 мкм)":
        f_mkm = st.slider("Размер фокуса (мкм)", 1, 100, f_def)
    else:
        f_mkm = st.slider("Размер фокуса (мм)", 0.1, 3.0, f_def/10 if f_def > 10 else 0.4, 0.1) * 1000
    
    st.header("📲 Детектор")
    pixel = st.number_input("Пиксель (мкм)", value=get_param("px", 64))
    mtf_k = st.slider("MTF (размытие)", 1.0, 3.0, float(query_params.get("mtf", 1.6)))
    srb_det = pixel * mtf_k

    st.header("📐 Геометрия и Объект")
    fdd = st.slider("FDD (мм)", 200, 1000, get_param("fdd", 600))
    obj_size = st.slider("Габарит образца (мм)", 1, 100, get_param("obj", 20))
    wall_w = st.slider("Толщина стенок (мм)", 1, 100, get_param("w", 10))
    
    mat_idx = mat_list.index(query_params.get("mat", "Алюминий")) if query_params.get("mat") in mat_list else 0
    material = st.selectbox("Материал", mat_list, index=mat_idx)

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

# --- ИНТЕРФЕЙС ВЫВОДА ---
st.title("🔬 Продвинутый NDT & Микрофокус v13")
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Оптим. позиция", f"{b_opt:.1f} мм"); st.caption(f"M = {m_val:.2f}")
with c2: st.metric("SRb (Центр)", f"{res_center:.1f} мкм"); st.write("✅ Класс B" if res_worst <= limit_b else "❌ Вне B")
with c3: st.metric("Худшее (Края)", f"{res_worst:.1f} мкм"); st.caption(f"Лимит B: {limit_b} мкм")
with c4: st.metric("Сложность", f"{materials[material]*(wall_w/10):.1f} x")

# График
fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="SRb на объекте", line=dict(width=3, color='#1f77b4')))
fig.add_vrect(x0=max(0, b_opt-obj_size/2), x1=min(fdd, b_opt+obj_size/2), fillcolor="rgba(255, 127, 14, 0.2)", line_width=0)
fig.add_hline(y=limit_b, line_dash="dot", line_color="green")
st.plotly_chart(fig, use_container_width=True)

# --- ГЕНЕРАЦИЯ ССЫЛКИ И ТЕКСТА ---
st.divider()
col_share1, col_share2 = st.columns(2)

with col_share1:
    st.subheader("🔗 Поделиться расчетом")
    # Формируем параметры для URL
    p_type = "micro" if src_type.startswith("Микро") else "macro"
    params = {
        "type": p_type,
        "f": int(f_mkm),
        "px": int(pixel),
        "mt": mtf_k,
        "fdd": fdd,
        "obj": obj_size,
        "w": wall_w,
        "mat": material
    }
    encoded_params = urllib.parse.urlencode(params)
    share_url = f"https://xn----7sbfnbafpc1ayjko0j.streamlit.app?{encoded_params}" # Сюда подставится ваш адрес
    
    st.info("Скопируйте URL из адресной строки браузера — он уже содержит все ваши настройки!")
    st.text_input("Ваша прямая ссылка на этот расчет:", value=share_url)

with col_share2:
    st.subheader("📝 Текстовый протокол")
    report = f"""ПРОТОКОЛ NDT (ISO 17636-2)
---------------------------
Материал: {material} ({wall_w} мм)
Источник: {f_mkm} мкм, FDD: {fdd} мм
Детектор: {pixel} мкм (MTF={mtf_k})
---------------------------
Оптимум (b): {b_opt:.1f} мм
Увеличение (M): {m_val:.2f}
Разрешение: {res_center:.1f} мкм
Статус: {"✅ СООТВЕТСТВУЕТ B" if res_worst <= limit_b else "❌ НЕ СООТВЕТСТВУЕТ"}
---------------------------"""
    st.code(report)

