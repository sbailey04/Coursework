################################################
#                                              #
#  Automated Observation Map Generator Script  #
#                                              #
#            Author: Sam Bailey                #
#        Last Revised: Mar 06, 2022            #
#                                              #
#         Created in late Jan, 2022            #
#                                              #
################################################

from datetime import datetime, timedelta
from io import StringIO
from urllib.request import urlopen
from siphon.simplewebservice.iastate import IAStateUpperAir

import cartopy.crs as ccrs
from metpy.io import add_station_lat_lon
from metpy.io import metar
from metpy.plots import declarative
from metpy.units import units
import pandas as pd
from collections import Counter
import math
import os
import sys
from PIL import Image
import json

# Retrieving and setting the current UTC time
currentTime = datetime.utcnow()
print(f"> It is currently {currentTime}Z")

# User Input
prevInput = 'n'
if os.path.isfile("Previous_Settings.json"):
    with open("Previous_Settings.json", "r") as ps:
        prevSet = json.load(ps)
    if "Obs" in prevSet:
        prevObsList = prevSet["Obs"].split('; ')
        prevInput = input("> Would you like to use the previous entry [y/n, default 'n']: ")
        if prevInput == 'y':
            levelInputPrev = prevObsList[0]
            inputDatePrev = prevObsList[1]
            dewPrev = prevObsList[2]
            areaPrev = prevObsList[3]
            dpiSet0Prev = prevObsList[4]
            scale0Prev = prevObsList[5]
            prfactor0Prev = prevObsList[6]
            projectionInputPrev = prevObsList[7]
    
        
        
if prevInput == 'y':
    levelInput = input(f"> Input the map level you would like to create, or input 'surface' for a surface-level map [Prev: {levelInputPrev}]: ")
else:
    levelInput = input("> Input the map level you would like to create, or input 'surface' for a surface-level map: ")
if (prevInput == 'y') and (levelInput == ''):
    levelInput = levelInputPrev
if levelInput != 'surface':
    level = int(levelInput)
else:
    level = levelInput


if prevInput == 'y':
    inputDate = input(f"> Input the map date in the format 'YYYY, MM, DD, HH', type 'today, HH', or type 'recent' for the most recent map [Prev: {inputDatePrev}]: ")
else:
    inputDate = input("> Input the map date in the format 'YYYY, MM, DD, HH', type 'today, HH', or type 'recent' for the most recent map: ")
if (prevInput == 'y') and (inputDate == ''):
    inputDate = inputDatePrev

if inputDate == 'recent':
    if level == 'surface':
        if currentTime.hour >= 21:
            hour = 21
        elif currentTime.hour >= 18:
            hour = 18
        elif currentTime.hour >= 15:
            hour = 15
        elif currentTime.hour >= 12:
            hour = 12
        elif currentTime.hour >= 9:
            hour = 9
        elif currentTime.hour >= 6:
            hour = 6
        elif currentTime.hour >= 3:
            hour = 3
        else:
            hour = 0
    else:
        if currentTime.hour >= 12:
            hour = 12
        else:
            hour = 0
    year = currentTime.year
    month = currentTime.month
    day = currentTime.day
else:
    parseDate1 = list(inputDate.split(", "))
    if parseDate1[0] == 'today':
        year = currentTime.year
        month = currentTime.month
        day = currentTime.day
        hour = int(parseDate1[1])
    else:
        parseDate2 = map(int, parseDate1)
        parsedDate = list(parseDate2)
        year = parsedDate[0]
        month = parsedDate[1]
        day = parsedDate[2]
        hour = parsedDate[3]
inputTime = datetime(year, month, day, hour)
daystamp = f"{year}-{inputTime.strftime('%m')}-{inputTime.strftime('%d')}"
timestampNum = f"{year}-{inputTime.strftime('%m')}-{inputTime.strftime('%d')}-{inputTime.strftime('%H')}Z"
timestampAlp = f"{inputTime.strftime('%b')} {day}, {year} - {hour}Z"


if (inputTime < datetime(1931, 1, 2)):
    sys.exit(">!< The date you entered is out of range!")


dew = False
if level != 'surface':
    if prevInput == 'y':
        dew = input(f"> Would you like to use dewpoint temperature or dewpoint depression [y/n, 'n' default, Prev: {dewPrev}]: ")
    else:
        dew = input("> Would you like to use dewpoint temperature or dewpoint depression [y/n, 'n' default]: ")
    if (prevInput == 'y') and (dew == ''):
        dew = dewPrev
    if dew == 'y':
        dew = True
    

if prevInput == 'y':
    area = input(f"> Select map area [Prev: {areaPrev}]: ")
else:
    area = input("> Select map area: ")
if (prevInput == 'y') and (area == ''):
    area = areaPrev


if prevInput == 'y':
    dpiSet0 = input(f"> Input map dpi [default 150, Prev: {dpiSet0Prev}]: ")
else:
    dpiSet0 = input("> Input map dpi [default 150]: ")
if (prevInput == 'y') and (dpiSet0 == ''):
    dpiSet0 = dpiSet0Prev
if (dpiSet0 == '') or (dpiSet0 == 'default'):
    dpiSet = 150
else:
    dpiSet = dpiSet0


if prevInput == 'y':
    scale0 = input(f"> Select the map scale [default 1.3, Prev: {scale0Prev}]: ")
else:
    scale0 = input("> Select the map scale [default 1.3]: ")
if (prevInput == 'y') and (scale0 == ''):
    scale0 = scale0Prev
if scale0 == '':
    scale = 1.3
else:
    scale = float(scale0)


if prevInput == 'y':
    prfactor0 = input(f"> Enter the station reduction factor [default 0.75, Prev: {prfactor0Prev}]: ")
else:
    prfactor0 = input("> Enter the station reduction factor [default 0.75]: ")
if (prevInput == 'y') and (prfactor0 == ''):
    prfactor0 = prfactor0Prev
if (prfactor0 == '') or (prfactor0 == 'default'):
    prfactor = 0.75
else:
    prfactor = float(prfactor0)


if prevInput == 'y':
    projectionInput = input(f"> Enter the code for the map projection you would like to use [default 'custom', Prev: {projectionInputPrev}]: ")
else:
    projectionInput = input("> Enter the code for the map projection you would like to use [default 'custom']: ")
if (prevInput == 'y') and (projectionInput == ''):
    projectionInput = projectionInputPrev

saveQuery = input("> Would you like to 'save' this map? [y/n, default 'y']: ")
if saveQuery != 'n':
    saveQuery = 'y'
if saveQuery == 'y':
    assigned = input("> Is this a map for an assignment? [y/n, default 'n']: ")
else:
    assigned = 'n'
    
# Handling the recent settings file
if os.path.isfile("Previous_Settings.json") == False:
    with open("Previous_Settings.json", "x") as newFile:
        newFile.writelines(["{", "}"])

with open("Previous_Settings.json", "r") as prevFile:
    prev = json.load(prevFile)
    
prev["Obs"] = f"{levelInput}; {inputDate}; {dew}; {area}; {dpiSet0}; {scale0}; {prfactor0}; {projectionInput}"

with open ("Previous_Settings.json", "w") as prevFile:
    json.dump(prev, prevFile)


# Read Data
date = datetime(year, month, day, hour)

# Data Acquisition
if level == 'surface':
    if year < 2019:
        df = pd.read_csv(f'http://bergeron.valpo.edu/archive_surface_data/{date:%Y}/{date:%Y%m%d}_metar.csv', parse_dates=['date_time'], na_values=[-9999], low_memory=False)
        weather_format = 'present_weather'
    else:
        data = StringIO(urlopen('http://bergeron.valpo.edu/current_surface_data/'f'{date:%Y%m%d%H}_sao.wmo').read().decode('utf-8', 'backslashreplace'))
        df = metar.parse_metar_file(data, year=date.year, month=date.month)
        weather_format = 'current_wx1_symbol'
    df['tmpf'] = (df.air_temperature.values * units.degC).to('degF')
    df['dwpf'] = (df.dew_point_temperature.values * units.degC).to('degF')
else:
    df = IAStateUpperAir.request_all_data(date)
    df = add_station_lat_lon(df, 'station').dropna(subset=['latitude', 'longitude'])
    df = df[df.station != 'KVER'] # "central Missouri" station that shouldn't be there, due to faulty lat-lon data
    df['dewpoint_depression'] = df['temperature'] - df['dewpoint']




# Format
mslp_formatter = lambda v: format(v*10, '.0f')[-3:]

if level != 'surface':
    if (level == 975) or (level == 850) or (level == 700):
        height_format = lambda v: format(v, '.0f')[1:]
    elif (level == 500) or (level == 300):
        height_format = lambda v: format(v, '.0f')[:-1]
    elif level == 200:
        height_format = lambda v: format(v, '.0f')[1:-1]


# Plot desired data
obs = declarative.PlotObs()
obs.data = df
obs.time = date
if level != 'surface':
    obs.level = level * units.hPa
    if dew:
        obs.fields = ['temperature', 'dewpoint', 'height']
        obs.colors = ['crimson', 'green', 'darkslategrey']
    else:
        obs.fields = ['temperature', 'dewpoint_depression', 'height']
        obs.colors = ['crimson', 'green', 'darkslategrey']
    obs.locations = ['NW', 'SW', 'NE']
    obs.formats = [None, None, height_format]
    obs.vector_field = ['u_wind', 'v_wind']
else:
    obs.time_window = timedelta(minutes=15)
    obs.level = None
    obs.fields = ['cloud_coverage', 'tmpf', 'dwpf', 'air_pressure_at_sea_level', f'{weather_format}'] # Archive data still stored as 'present_weather', but is now stored as 'current_wx1_symbol' in MetPy.
    obs.colors = ['black', 'crimson', 'green', 'darkslategrey', 'indigo']
    obs.locations = ['C', 'NW', 'SW', 'NE', 'W']
    obs.formats = ['sky_cover', None, None, mslp_formatter, 'current_weather']
    obs.vector_field = ['eastward_wind', 'northward_wind']
obs.reduce_points = prfactor

# Custom panel.area definitions
panel = declarative.MapPanel()

with open("Custom_Area_Definitions.json", "r") as ad:
    areaDict = json.load(ad)
area_dictionary = dict(areaDict)
area_dictionary = {k: tuple(map(float, v.split(", "))) for k, v in area_dictionary.items()}

# Panel for plot with Map features
panel.layout = (1, 1, 1)
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
else:
    panel.area = f'{area}'
panel.layers = ['states', 'coastline']
panel.plots = [obs]
if level != 'surface':
    panel.title = f'Bailey, Sam - {area} {level}mb Map {timestampAlp}'
else:
    panel.title = f'Bailey, Sam - {area} Surface Map {timestampAlp}'


# Parsing the panel.area into a list, and doing math on it.
areaList = list(panel.area)
areaMap = map(int, areaList)
mapList = list(areaMap)
diffLat = int(mapList[1])-int(mapList[0])
diffLon = int(mapList[3])-int(mapList[2])
avgDiff = ((diffLat + diffLon)//2)
scaledDiff = math.floor(avgDiff*scale)

# Determining projection
midLon = (mapList[1]+mapList[0])//2
midLat = (mapList[3]+mapList[2])//2
if projectionInput == '' or projectionInput == 'custom':
    projection = ccrs.LambertConformal(central_longitude = midLon, central_latitude = midLat)
else:
    projection = projectionInput
panel.projection = projection # ccrs.LambertConformal(central_longitude = midLon, central_latitude = midLat), mer, ps, lcc


# Bringing it all together
pc = declarative.PanelContainer()
pc.size = (scaledDiff, scaledDiff)
pc.panels = [panel]


# Parsing assignment status to determine save location
if assigned == 'y':
    saveLocale = 'Assignment_Maps'
else:
    saveLocale = 'Test_Maps'

OldDir = os.path.isdir(f'../Maps/{saveLocale}/{daystamp}')

if saveQuery == 'y':
    if OldDir == False:
        os.mkdir(f'../Maps/{saveLocale}/{daystamp}')
    if level != 'surface':
        pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {area} {level}mb Map, {dpiSet} DPI - Bailey, Sam.png', dpi=dpiSet, bbox_inches='tight')
        save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {area} {level}mb Map, {dpiSet} DPI - Bailey, Sam.png')
        save.show()
    else:
        pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {area} Surface Map, {dpiSet} DPI - Bailey, Sam.png', dpi=dpiSet, bbox_inches='tight')
        save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {area} Surface Map, {dpiSet} DPI - Bailey, Sam.png')
        save.show()
    print("> Map successfully saved!")
else:
    if level != 'surface':
        pc.save(f'../Maps/{saveLocale}/{timestampNum}, {area} {level}mb Map, {dpiSet} DPI - Bailey, Sam.png', dpi=dpiSet, bbox_inches='tight')
        save = Image.open(f'../Maps/{saveLocale}/{timestampNum}, {area} {level}mb Map, {dpiSet} DPI - Bailey, Sam.png')
        save.show()
        os.remove(f'../Maps/{saveLocale}/{timestampNum}, {area} {level}mb Map, {dpiSet} DPI - Bailey, Sam.png')
    else:
        pc.save(f'../Maps/{saveLocale}/{timestampNum}, {area} Surface Map, {dpiSet} DPI - Bailey, Sam.png', dpi=dpiSet, bbox_inches='tight')
        save = Image.open(f'../Maps/{saveLocale}/{timestampNum}, {area} Surface Map, {dpiSet} DPI - Bailey, Sam.png')
        save.show()
        os.remove(f'../Maps/{saveLocale}/{timestampNum}, {area} Surface Map, {dpiSet} DPI - Bailey, Sam.png')