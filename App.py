import streamlit as st
import ezdxf
import math
import numpy as np
from scipy.spatial import Voronoi
from io import BytesIO, StringIO
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. ЗАЩИТА ПАРОЛЕМ ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🔐 ArtMetal Tallinn: Вход")
        st.text_input("Пароль доступа", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

if not check_password():
    st.stop()

# --- 2. ПОДКЛЮЧЕНИЕ К ОБЛАКУ (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def save_order(data):
    try:
        # Пытаемся прочитать таблицу (указываем имя листа, обычно это "Sheet1")
        # ttl=0 заставляет программу не кешировать старые данные, а видеть таблицу онлайн
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
        
        # Создаем новую строку
        new_row = pd.DataFrame([data])
        
        # Объединяем старое с новым
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        
        # Записываем обратно в облако
        conn.update(worksheet="Sheet1", data=updated_df)
        st.success("✅ ЗАКАЗ СОХРАНЕН В GOOGLE SHEETS!")
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")
        st.info("Проверь: 1. Доступ 'Редактор' в таблице. 2. Название листа должно быть 'Sheet1'.")
# --- 3. ЛОГИКА И ОТРИСОВКА ---
class MetalLogic:
    def __init__(self):
        self.materials = {
            "Сталь": {"density": 7850, "price": 1.6},
            "Алюминий": {"density": 2700, "price": 4.8},
            "Нержавейка": {"density": 8000, "price": 6.0}
        }

    def get_stats(self, file_bytes):
        try:
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
                elif e.dxftype() == 'CIRCLE':
                    length += 2 * math.pi * e.dxf.radius
            return length / 1000, doc
        except:
            return 0, None

def draw_dxf(doc):
    fig, ax = plt.subplots(figsize=(8, 8))
    msp = doc.modelspace()
    for e in msp:
        if e.dxftype() == 'LINE':
            ax.plot([e.dxf.start.x, e.dxf.end.x], [e.dxf.start.y, e.dxf.end.y], color='black', lw=0.7)
        elif e.dxftype() == 'LWPOLYLINE':
            pts = np.array(list(e.get_points()))
            ax.plot(pts[:, 0], pts[:, 1], color='black', lw=0.7)
        elif e.dxftype() == 'CIRCLE':
            c = plt.Circle((e.dxf.center.x, e.dxf.center.y), e.dxf.radius, color='black', fill=False, lw=0.7)
            ax.add_patch(c)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig

# --- 4. ГЕНЕРАТОРЫ ДИЗАЙНА ---
def generate_voronoi(w, h, pts_count):
    # 1. Генерируем точки внутри области
    points = np.random.rand(pts_count, 2) * [w, h]
    
    # 2. Добавляем точки далеко за границами для корректных краев
    far = np.array([[-w*2, -h*2], [-w*2, h*3], [w*3, h*3], [w*3, -h*2]])
    points = np.vstack([points, far])
    
    vor = Voronoi(points)
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # 3. Перебираем ребра (ridges)
    for ridge in vor.ridge_vertices:
        # Проверяем, что ребро имеет ровно 2 вершины и они не "бесконечные" (-1)
        if len(ridge) == 2 and -1 not in ridge:
            v1_raw = vor.vertices[ridge[0]]
            v2_raw = vor.vertices[ridge[1]]
            
            # Проверка: обе точки должны быть внутри листа [w, h]
            if (0 <= v1_raw[0] <= w and 0 <= v1_raw[1] <= h and 
                0 <= v2_raw[0] <= w and 0 <= v2_raw[1] <= h):
                
                # Превращаем в чистые числа для ezdxf
                p1 = (float(v1_raw[0]), float(v1_raw[1]))
                p2 = (float(v2_raw[0]), float(v2_raw[1]))
                
                msp.add_line(p1, p2)
                
    # 4. Рисуем рамку листа
    msp.add_lwpolyline([(0, 0), (float(w), 0), (float(w), float(h)), (0, float(h)), (0, 0)])
    return doc
# --- 5. ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="ArtMetal Cloud Pro", page_icon="⚒️")
logic = MetalLogic()

st.sidebar.title("⚒️ ArtMetal Pro")
st.sidebar.write("📍 **Tallinn, Lasnamäe / TTÜ**")
st.sidebar.info("Система управления заказами v2.0")

tab1, tab2, tab3 = st.tabs(["💰 Калькулятор", "🎨 Дизайн", "📊 История заказов"])

with tab1:
    st.header("Расчет стоимости")
    col1, col2 = st.columns(2)
    with col1:
        mat_name = st.selectbox("Металл", list(logic.materials.keys()))
        thick = st.number_input("Толщина (мм)", 0.5, 30.0, 3.0)
        area = st.number_input("Площадь (м2)", 0.01, 10.0, 0.5)
        speed = st.slider("Скорость резки (м/мин)", 0.1, 5.0, 0.5)
    
    with col2:
        dxf_file = st.file_uploader("Загрузить чертеж", type="dxf")
        manual_len = st.number_input("Или введи длину реза (м)", 0.0, 500.0, 0.0)

    if st.button("РАССЧИТАТЬ СТОИМОСТЬ", type="primary"):
        cut_len, doc = (logic.get_stats(dxf_file) if dxf_file else (manual_len, None))
        
        mat = logic.materials[mat_name]
        weight = area * (thick / 1000) * mat["density"]
        mat_cost = weight * mat["price"] * 1.1
        work_time = cut_len / speed
        work_cost = (work_time / 60) * 50.0
        total = round(mat_cost + work_cost, 2)

        if doc: st.pyplot(draw_dxf(doc))
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Вес", f"{round(weight, 1)} кг")
        c2.metric("Длина реза", f"{round(cut_len, 2)} м")
        c3.metric("ИТОГО", f"{total} €")

        if st.button("💾 СОХРАНИТЬ В ОБЛАКО"):
            order_data = {
                "Дата": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "Материал": mat_name,
                "Вес": round(weight, 2),
                "Длина_реза": round(cut_len, 2),
                "Цена": total
            }
            save_order(order_data)

with tab2:
    st.header("Генератор дизайна")
    mode = st.radio("Стиль", ["Паутина Вороного", "Перфорация Круги"])
    gw = st.number_input("Ширина (мм)", 100, 2000, 500)
    gh = st.number_input("Высота (мм)", 100, 2000, 1000)

    if mode == "Паутина Вороного":
        gpts = st.slider("Плотность", 5, 150, 40)
        if st.button("Создать паутину"):
            new_doc = generate_voronoi(gw, gh, gpts)
            st.pyplot(draw_dxf(new_doc))
            out = StringIO()
            new_doc.write(out)
            st.download_button("📥 СКАЧАТЬ DXF", out.getvalue(), "pattern.dxf")
    else:
        radius = st.slider("Радиус (мм)", 2, 50, 10)
        step = st.slider("Шаг (мм)", 5, 100, 25)
        if st.button("Создать перфорацию"):
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            for x in range(step, gw, step):
                for y in range(step, gh, step): msp.add_circle((x, y), radius)
            msp.add_lwpolyline([(0,0), (gw,0), (gw,gh), (0,gh), (0,0)])
            st.pyplot(draw_dxf(doc))
            out = StringIO()
            doc.write(out)
            st.download_button("📥 СКАЧАТЬ DXF", out.getvalue(), "circles.dxf")

with tab3:
    st.header("Журнал заказов в реальном времени")
    if st.button("🔄 ОБНОВИТЬ ДАННЫЕ"):
        st.cache_data.clear() # Очищаем память приложения
        
    try:
        # ttl=0 — это "Time To Live" в 0 секунд, то есть данные всегда свежие
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        if df.empty:
            st.info("Таблица подключена, но в ней пока нет записей.")
        else:
            st.dataframe(df, use_container_width=True)
            
            # Добавим общую сумму всех заказов для статистики
            if "Цена" in df.columns:
                total_sum = pd.to_numeric(df["Цена"], errors='coerce').sum()
                st.metric("Общая сумма заказов в базе", f"{round(total_sum, 2)} €")
    except Exception as e:
        st.error(f"Не удалось прочитать таблицу: {e}")
        st.info("Проверь: 1. Имя листа в Google Sheets (должно быть Sheet1). 2. Доступ по ссылке (Редактор).")



