import streamlit as st
import ezdxf
import math
from io import BytesIO

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # удаляем пароль из памяти
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Введите пароль доступа", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Введите пароль доступа", type="password", on_change=password_entered, key="password")
        st.error("😕 Неверный пароль")
        return False
    else:
        return True

if not check_password():
    st.stop()  # Дальше код не пойдет, пока не введешь пароль

# ТВОЙ ОСНОВНОЙ КОД НАЧИНАЕТСЯ ЗДЕСЬ...
st.success("Доступ разрешен. Привет, Мастер!")

# --- ЛОГИКА РАСЧЕТА ---
def get_dxf_length(file_bytes):
    try:
        # Читаем файл из памяти (загрузка через браузер)
        doc = ezdxf.readfile(BytesIO(file_bytes.read()))
        msp = doc.modelspace()
        length = 0
        for e in msp:
            if e.dxftype() == 'LINE':
                length += math.dist(e.dxf.start, e.dxf.end)
            elif e.dxftype() == 'LWPOLYLINE':
                pts = e.get_points()
                for i in range(len(pts)-1):
                    length += math.dist(pts[i], pts[i+1])
            elif e.dxftype() == 'ARC':
                length += math.radians(e.dxf.end_angle - e.dxf.start_angle) * e.dxf.radius
            elif e.dxftype() == 'CIRCLE':
                length += 2 * math.pi * e.dxf.radius
        return length / 1000 # в метры
    except:
        return 0

# --- ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="ArtMetal Calc Tallinn", page_icon="⚒️")
st.title("⚒️ Калькулятор ArtMetal")
st.write("Профессиональный расчет себестоимости изделий из металла")

# Боковая панель с настройками цен
with st.sidebar:
    st.header("Настройки цен")
    steel_price = st.number_input("Цена стали (€/кг)", value=1.6)
    al_price = st.number_input("Цена алюминия (€/кг)", value=4.8)
    work_rate = st.number_input("Стоимость часа работы (€)", value=45.0)

# Основная форма
col1, col2 = st.columns(2)

with col1:
    material = st.selectbox("Материал", ["Сталь", "Алюминий"])
    thickness = st.number_input("Толщина (мм)", min_value=0.5, value=3.0)
    area = st.number_input("Площадь листа (м2)", min_value=0.01, value=0.5)

with col2:
    uploaded_file = st.file_uploader("Загрузи DXF чертеж", type="dxf")
    manual_cut = st.number_input("Или введи длину реза вручную (м)", value=0.0)

# Кнопка расчета
if st.button("РАССЧИТАТЬ СТОИМОСТЬ", type="primary"):
    # Определяем длину реза
    if uploaded_file:
        cut_len = get_dxf_length(uploaded_file)
        st.success(f"Длина реза из файла: {round(cut_len, 2)} м")
    else:
        cut_len = manual_cut

    # Физика
    density = 7850 if material == "Сталь" else 2700
    price_per_kg = steel_price if material == "Steel" else al_price
    
    weight = area * (thickness / 1000) * density
    mat_cost = weight * price_per_kg * 1.1
    work_time = (cut_len / 0.5) / 60
    work_cost = work_time * work_rate
    total = mat_cost + work_cost

    # Вывод результата
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Вес (кг)", f"{round(weight, 2)}")
    c2.metric("Работа (€)", f"{round(work_cost, 2)}")
    c3.metric("ИТОГО (€)", f"{round(total, 2)}", delta_color="off")