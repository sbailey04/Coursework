from metpy.plots import declarative

name = input("> Input the postal code area you would like the coordinates for: ")

panel = declarative.MapPanel()
panel.area = f'{name}'

print(panel.area)