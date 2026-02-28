import ezdxf
import math

class MetalCalculator:
    def __init__(self):
        # Цены и плотность (можно менять под рынок Эстонии)
        self.materials = {
            "1": {"name": "Сталь", "density": 7850, "price": 1.6},
            "2": {"name": "Алюминий", "density": 2700, "price": 4.8},
            "3": {"name": "Нержавейка", "density": 8000, "price": 5.5}
        }
        self.hourly_rate = 45.0  # Стоимость работы станка/часа

    def get_dxf_length(self, filename):
        """Считает общую длину всех линий в чертеже (метры)"""
        try:
            doc = ezdxf.readfile(filename)
            msp = doc.modelspace()
            length = 0
            for e in msp:
                if e.dxftype() == 'LINE':
                    length += math.dist(e.dxf.start, e.dxf.end)
                elif e.dxftype() == 'LWPOLYLINE':
                    pts = e.get_points()
                    for i in range(len(pts)-1):
                        length += math.dist(pts[i], pts[i+1])
            return length / 1000  # Перевод из мм в метры
        except Exception as e:
            print(f"Ошибка при чтении DXF: {e}")
            return 0

    def calculate(self, mat_choice, thickness, area, cut_length):
        mat = self.materials.get(mat_choice)
        
        # Расчет веса: Площадь * (Толщина/1000) * Плотность
        weight = area * (thickness / 1000) * mat["density"]
        mat_cost = weight * mat["price"] * 1.1  # +10% на обрезки
        
        # Расчет времени: Длина реза / Скорость (0.5м/мин)
        work_time_hours = (cut_length / 0.5) / 60
        work_cost = work_time_hours * self.hourly_rate
        
        return {
            "material": mat["name"],
            "weight": round(weight, 2),
            "mat_cost": round(mat_cost, 2),
            "work_cost": round(work_cost, 2),
            "total": round(mat_cost + work_cost, 2)
        }
