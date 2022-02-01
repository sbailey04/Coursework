#!/usr/bin/env python
# coding: utf-8

# # Surface Data and Plotting
# 

from datetime import datetime, timedelta
from io import StringIO
from urllib.request import urlopen

from metpy.io import metar
from metpy.plots import declarative
from metpy.units import units
import pandas as pd
import math

# Retrieving and setting the current UTC time
currentTime = datetime.utcnow()
print(f"It is currently {currentTime}Z")

# User Input
inputDate = input("Input the map date in the format 'YYYY, MM, DD, HH', or type 'recent' for the most recent map: ")
if inputDate == 'recent':
    if currentTime.hour > 21:
        hour = 21
    elif currentTime.hour > 18:
        hour = 18
    elif currentTime.hour > 15:
        hour = 15
    elif currentTime.hour > 12:
        hour = 12
    elif currentTime.hour > 9:
        hour = 9
    elif currentTime.hour > 6:
        hour = 6
    elif currentTime.hour > 3:
        hour = 3
    else:
        hour = 0
    year = currentTime.year
    month = currentTime.month
    day = currentTime.day
else:
    parseDate1 = list(inputDate.split(", "))
    parseDate2 = map(int, parseDate1)
    parsedDate = list(parseDate2)
    year = parsedDate[0]
    month = parsedDate[1]
    day = parsedDate[2]
    hour = parsedDate[3]
    
area = input("Select map area: ")
#dimensions = int(input("Input map dimensions: "))

dpiSet0 = input("Input map dpi [default 150]: ")
if dpiSet0 == '':
    dpiSet = 150
else:
    dpiSet = dpiSet0
    
scale0 = input("Select the map scale [default 1.3]: ")
if scale0 == '':
    scale = 1.3
else:
    scale = float(scale0)

prfactor0 = input("Enter the station reduction factor [0.75 default]: ")
if prfactor0 == '':
    prfactor = 0.75
else:
    prfactor = float(prfactor0)

assigned = input("Is this a map for an assignment? [y/n, default 'n']: ")


# Read Data
date = datetime(year, month, day, hour)


# Download current data from http://bergeron.valpo.edu/current_surface_data and upload to your Jupyterhub space.
data = StringIO(urlopen('http://bergeron.valpo.edu/current_surface_data/'
                        f'{date:%Y%m%d%H}_sao.wmo').read().decode('utf-8', 'backslashreplace'))
df = metar.parse_metar_file(data, year=date.year, month=date.month)
# We bring in surface data that is in METAR format and store it for approximately two weeks in `/data/ldmdata/surface/sao` and the format of the filenames are `YYYYMMDDHH_sao.wmo` where `YYYY` is the year, `MM` is the month, `DD` is the day, and `HH` is the hour. Or there are pre-decoded files located in `/data/ldmdata/surface/csv` and can be read in using the Pandas module.
# Read with pandas, note differences from METAR files
# df = pd.read_csv(f'http://bergeron.valpo.edu/archive_surface_data/{date:%Y}/{date:%Y%m%d}_metar.csv', parse_dates=['date_time'], na_values=[-9999], low_memory=False)

df['tmpf'] = (df.air_temperature.values * units.degC).to('degF')
df['dwpf'] = (df.dew_point_temperature.values * units.degC).to('degF')


# Format
mslp_formatter = lambda v: format(v*10, '.0f')[-3:]


# Plot desired data
obs = declarative.PlotObs()
obs.data = df
obs.time = date
obs.time_window = timedelta(minutes=15)
obs.level = None
obs.fields = ['cloud_coverage', 'tmpf', 'dwpf', 'air_pressure_at_sea_level', 'current_wx1_symbol'] # Archive data still stored as 'present_weather', but is now stored as 'current_wx1_symbol' in MetPy.
obs.locations = ['C', 'NW', 'SW', 'NE', 'W']
obs.formats = ['sky_cover', None, None, mslp_formatter, 'current_weather']
obs.reduce_points = prfactor
obs.vector_field = ['eastward_wind', 'northward_wind']


# Panel for plot with Map features
panel = declarative.MapPanel()
panel.layout = (1, 1, 1)
panel.projection = 'lcc'
panel.area = f'{area}'
panel.layers = ['states']
panel.plots = [obs]
panel.title = f'Bailey, Sam - Surface Map {obs.time}Z, {area}'


# Parsing the panel.area into a list, and doing math on it.
areaList = list(panel.area)
areaMap = map(int, areaList)
mapList = list(areaMap)
diffLat = int(mapList[1])-int(mapList[0])
diffLon = int(mapList[3])-int(mapList[2])
avgDiff = ((diffLat + diffLon)//2)
scaledDiff = math.floor(avgDiff*scale)


# Bringing it all together
pc = declarative.PanelContainer()
pc.size = (scaledDiff, scaledDiff)
pc.panels = [panel]


# Parsing assignment status to determine save location
if assigned == 'y':
    saveLocale = 'Assignment Maps'
else:
    saveLocale = 'Test Maps'

pc.save(f'/home/sbailey4/Documents/met130/Maps/{saveLocale}/Surface Map - {obs.time}Z, {area}, {dpiSet} DPI - Bailey, Sam.png', dpi=dpiSet, bbox_inches='tight')


# Assorted other useful - or potentially useful - commands.
# df.keys for the applicable displayable variables.
# pc.show()