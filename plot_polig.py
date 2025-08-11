from shapely.geometry import Polygon
import matplotlib.pyplot as plt

coords = [
    (-47.919273, -21.493102),
    (-47.919273, -21.467767),
    (-47.901859, -21.467767),
    (-47.901859, -21.493102)
]

polygon = Polygon(coords)

x, y = polygon.exterior.xy
plt.plot(x, y)
plt.title("Polígono estendido para baixo")
plt.grid(True)
plt.show()
