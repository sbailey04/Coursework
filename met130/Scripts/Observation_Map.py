################################################
#                                              #
#  Automated Observation Map Generator Script  #
#                                              #
#            Author: Sam Bailey                #
#        Last Revised: Mar 02, 2022            #
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
from PIL import Image

# Retrieving and setting the current UTC time
currentTime = datetime.utcnow()
print(f"> It is currently {currentTime}Z")

# User Input
prevInput = input("> Would you like to use the previous entry [y/n, default 'n']: ")
if prevInput == 'y':
    prevObs = open('prevObs.txt', 'r')
    prevObsStored = prevObs.readlines()
    count = 0
    prevObsList = []
    for line in prevObsStored:
        prevObsList.append(line.strip())
        count += 1
    levelInput = prevObsList[0]
    inputDate = prevObsList[1]
    dew = prevObsList[2]
    area = prevObsList[3]
    dpiSet0 = prevObsList[4]
    scale0 = prevObsList[5]
    prfactor0 = prevObsList[6]
    projectionInput = prevObsList[7]
    
        
        
if prevInput != 'y':
    levelInput = input("> Input the map level you would like to create, or input 'surface' for a surface-level map: ")
if levelInput != 'surface':
    level = int(levelInput)
else:
    level = levelInput

if prevInput != 'y':
    inputDate = input("> Input the map date in the format 'YYYY, MM, DD, HH', type 'today, HH', or type 'recent' for the most recent map: ")
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
timestampNum = f"{year}-{inputTime.strftime('%m')}-{inputTime.strftime('%d')}-{hour}Z"
timestampAlp = f"{inputTime.strftime('%b')} {day}, {year} - {hour}Z"

dew = False
if prevInput != 'y':
    if level != 'surface':
        dew = input("> Would you like to use dewpoint temperature ['y'] or dewpoint depression [default]: ")
        if dew == 'y':
            dew = True
    
if prevInput != 'y':
    area = input("> Select map area: ")

if prevInput != 'y':
    dpiSet0 = input("> Input map dpi [default 150]: ")
if dpiSet0 == '':
    dpiSet = 150
else:
    dpiSet = dpiSet0

if prevInput != 'y':
    scale0 = input("> Select the map scale [default 1.3]: ")
if scale0 == '':
    scale = 1.3
else:
    scale = float(scale0)

if prevInput != 'y':
    prfactor0 = input("> Enter the station reduction factor [default 0.75]: ")
if prfactor0 == '':
    prfactor = 0.75
else:
    prfactor = float(prfactor0)

if prevInput != 'y':
    projectionInput = input("> Enter the code for the map projection you would like to use [default 'custom']: ")

saveQuery = input("> Would you like to 'save' this map? [y/n, default 'n']: ")
if saveQuery == 'y':
    assigned = input("> Is this a map for an assignment? [y/n, default 'n']: ")
else:
    assigned = 'n'
    
# Handling the recent settings file
if prevInput != 'y':
    if os.path.isfile("prevObs.txt"):
        os.remove("prevObs.txt")
    with open("prevObs.txt", "x") as prev:
        W = [f'{levelInput}\n', f'{inputDate}\n', f'{dew}\n', f'{area}\n', f'{dpiSet0}\n', f'{scale0}\n', f'{prfactor0}\n', f'{projectionInput}\n']
        prev.writelines(W)


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
area_dictionary = {'USc':(-120, -74, 25, 50),
                  'MW':(-94.5, -78.5, 35.5, 47)}

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


# Assorted other useful - or potentially useful - commands.
# df.keys for the applicable displayable variables.
# pc.show()