from metpy.plots import declarative
from collections import Counter

area = input("> Input the postal code area you would like the coordinates for: ")

area_dictionary = {'USc':(-120, -74, 25, 50),
                  'MW':(-94.5, -78.5, 35.5, 47)}

panel = declarative.MapPanel()
simArea = area.replace("+", "")
simArea = simArea.replace("-", "")
if simArea in area_dictionary:
    # Parse custom zoom feature
    splitArea = Counter(area)
    factor = (splitArea['+']) - (splitArea['-'])
    scaleFactor = (1 - 2**-factor)/2
    west, east, south, north = area_dictionary[f'{simArea}']
    newWest = west - (west - east) * scaleFactor
    newEast = east + (west - east) * scaleFactor
    newSouth = south - (south - north) * scaleFactor
    newNorth = north + (south - north) * scaleFactor
    modArea = newWest, newEast, newSouth, newNorth
    
    panel.area = modArea
    print(scaleFactor)
else:
    panel.area = f'{area}'

print(panel.area)