################################################
#                                              #
#MetPy Panel Definition to Coordinate Converter#
#                                              #
#            Author: Sam Bailey                #
#        Last Revised: Mar 06, 2022            #
#                                              #
#        Created in early Feb, 2022            #
#                                              #
################################################

from metpy.plots import declarative
from collections import Counter
import os
import json

area = input("> Input the postal code area you would like the coordinates for: ")

if os.path.isfile("config.json"):
    with open("config.json", "r") as cfg:
        config = json.load(cfg)
area_dictionary = dict(config['areas'])
area_dictionary = {k: tuple(map(float, v.split(", "))) for k, v in area_dictionary.items()}

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