################################################
#                                              #
#       Automated Map Generation Program       #
#                                              #
#            Author: Sam Bailey                #
#        Last Revised: Apr 12, 2022            #
#                Version 0.1.0                 #
#                                              #
#          Created on Mar 09, 2022             #
#                                              #
################################################

################################################
# New_Map.py, AMGP Version 0.1.0 Manual:       #
#                                              #
# This program creates .png weather maps from  #
# current, past, and model data from various   #
# sources.                                     #
# Run                                          #
# >>> python New_Map.py                        #
# to start the program in its default mode.    #
# The default preset from config.json will be  #
# loaded, and the loaded settings will be      #
# displayed. Type 'list' to see the accepted   #
# commands to go from there within the         #
# program.                                     #
#                                              #
# Alternatively, run                           #
# >>> python New_Map.py --quickrun {args}      #
# to create a singular map, or loop of maps,   #
# without opening the program.                 #
# >>> python New_Map.py -help                  #
# will print all accepted arguments and their  #
# usages to console.                           #
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
import metpy.calc as mpcalc
import xarray as xr
import pandas as pd
from collections import Counter
import numpy as np
import math
import os
import sys
from PIL import Image
import json

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

version = "0.1.0"

# Opening the config file
if os.path.isfile("config.json"):
    with open("config.json", "r") as cfg:
        config = json.load(cfg)
        
if os.path.isfile("manual.txt"):
    with open("manual.txt", "r") as man:
        manual = man.readlines()
else:
    manual = ['Manual not found...']

    
# Retrieving and setting the current UTC time
def setTime():
    global currentTime
    currentTime = datetime.utcnow()
    
def getTime():
    global currentTime
    currentTime = datetime.utcnow()
    print(f"<time> It is currently {currentTime}Z")

# Definitions
def inputChain():
    global loadedLevel
    global loadedDate
    global loadedDelta
    global loadedFactors
    global loadedArea
    global loadedDPI
    global loadedScale
    global loadedPRF
    global loadedBF
    global loadedSmooth
    global loadedProjection
    global title
    global noShow
    
    print("<menu> Input commands, or type 'help'.")
    comm = input("<input> ")
    
    command = comm.split(" ")
    
    if command[0] == "help":
        for line in list(range(1, 58, 1)):
#            if line != 22:
#                print(manual[line], end='')
#            else:
#                print(manual[line])
            print(manual[line], end='')
        inputChain()
    
    if command[0] == "list":
        print("<list> Type 'time' to set and print the current time.")
        print("<list> Type 'preset {name}' to load a map preset.")
        print("<list> Type 'preset list' to list available presets.")
        print("<list> Type 'factors' to list accepted map factors.")
        print("<list> Type 'paste' to see the currently loaded values.")
        print("<list> Type 'edit {parameter} {value}' to edit a loaded parameter.")
        print("<list> Type 'edit Factors {(optional) add/remove} {value}' to edit loaded factors.")
        print("<list> Type 'save {preset name}' to save the current settings as a preset.")
        print("<list> Type 'run' to run with the current settings.")
        print("<list> Type 'quit' to exit without running.")
        inputChain()
    
    
    if command[0] == 'time':
        getTime()
        inputChain()
    elif command[0] == 'preset':
        if command[1] == 'list':
            keys = str(list(config['presets'].keys()))
            print("<presets> Below is the list of all currently loaded presets:")
            print("<presets> " + keys)
            inputChain()
        else:
            presetLoad(command[1])
            paste()
            inputChain()
    elif command[0] == 'factors':
        print("<factors> 'temperature' - Observation station temps")
        print("<factors> 'dewpoint' - Observation station dewpoints")
        print("<factors> 'dewpoint_depression' - Observation station dewpoint depressions")
        print("<factors> 'height' - Observation station pressure heights (upper-air only)")
        print("<factors> 'pressure' - Observation station pressures (surface only)")
        print("<factors> 'current_weather' - Observation station weather (surface only)")
        print("<factors> 'barbs' - Observation station wind")
        print("<factors> 'cloud_coverage' - Observation station cloud coverage (surface only)")
        print("<factors> 'height_contours' - Gridded pressure height contours (upper-air only)")
        print("<factors> 'temp_contours' - Gridded temperature contours")
        print("<factors> 'temp_fill' - Gridded temperature coloration fill")
        print("<factors> 'wind_fill' - Gridded winds as a plot fill")
        print("<factors> 'temp_advect_fill' - Gridded temperature advection")
        print("<factors> 'relative_vorticity_fill' - Gridded relative vorticity")
        print("<factors> 'absolute_vorticity_fill' - Gridded absolute vorticity (upper-air only)")
        print("<factors> 'pressure_contours' - Gridded pressure contours (surface only)")
        print("<factors> 'dew_contours' - Gridded dewpoint contours (surface only)")
        print("<factors> 'gridded_barbs' - Gridded winds")
        inputChain()
    elif command[0] == 'paste':
        paste()
        inputChain()
    elif command[0] == 'edit':
        loadedCommand = "loaded" + command[1]
        if loadedCommand in possibleFactors:
            if command[1] == "Level":
                loadedLevel = command[2]
            if command[1] == "Date":
                if command[2] == 'recent':
                    loadedDate = command[2]
                elif command[2] == "today":
                    loadedDate = f'{command[2]}, {command[3]}'
                else:
                    loadedDate = f'{command[2]}, {command[3]}, {command[4]}, {command[5]}'
            if command[1] == "Delta":
                loadedDelta = command[2]
            if command[1] == "Factors":
                blankFactors = []
                count = 0
                if command[2] == "add":
                    blankFactors = loadedFactors.split(', ')
                    for item in command:
                        if count > 2:
                            blankFactors.append(command[count])
                        count += 1
                elif command[2] == "remove":
                    blankFactors = loadedFactors.split(', ')
                    for item in command:
                        if count > 2:
                            if command[count] in blankFactors:
                                blankFactors.pop(blankFactors.index(command[count]))
                            else:
                                print("<error> That is not a valid factor to remove!")
                                inputChain()
                        count += 1
                else:
                    for item in command:
                        if count > 1:
                            blankFactors.append(command[count])
                        count += 1
                fullFactors = ', '.join(blankFactors)
                loadedFactors = fullFactors
            if command[1] == "Area":
                loadedArea = command[2]
            if command[1] == "DPI":
                loadedDPI = command[2]
            if command[1] == "Scale":
                loadedScale = command[2]
            if command[1] == "PRF":
                loadedPRF = command[2]
            if command[1] == 'BF':
                loadedBF = command[2]
            if command[1] == "Smooth":
                loadedSmooth = command[2]
            if command[1] == "Projection":
                loadedProjection = command[2]
            paste()
            inputChain()
        else:
            print("<error> That is not a valid parameter to edit!")
            inputChain()
    elif command[0] == 'save':
        save(f'{command[1]}')
        print(f"<save> Loaded settings saved to config.json as preset: {command[1]}.")
        inputChain()
    elif command[0] == 'run':
        dosave = input("<run> Would you like to save this map? [y/n] ")
        if dosave == 'y':
            S = True
            assigned = input("<run> Is this map for an assignment? [y/n] ")
            if assigned == 'y':
                A = True
            else:
                A = False
            NS = input("<run> Would you like to show this map? [y/n] ")
            if NS == 'n':
                noShow = True
            else:
                noShow = False
            title = input("<run> If you would like to override the default title, type the override here. Otherwise, hit enter: ")
        else:
            S = False
            A = False
            title = ''
        save('prev')
        print("<run> Previous settings saved.")
        run(S, A, title, 0)
    #elif command[0] == 'mode':
        #multiMode()
    elif command[0] == 'quit':
        sys.exit("<quit> The process was terminated.")
    else:
        print("<error> That is not a valid command!")
        inputChain()
        
#def multiMode():
    ###

        
# Save a preset to the config file
def save(name):
    namei = {"level":f"{loadedLevel}","date":f"{loadedDate}","delta":f"{loadedDelta}","factors":f"{loadedFactors}","area":f"{loadedArea}","dpi":f"{loadedDPI}","scale":f"{loadedScale}","prfactor":f"{loadedPRF}","barbfactor":f"{loadedBF}","smoothing":f"{loadedSmooth}","projection":f"{loadedProjection}"}
    config['presets'][f'{name}'] = namei
    with open("config.json", "w") as J:
        json.dump(config, J)

# Load a preset from the config file
def presetLoad(loadedPreset):
    global loadedLevel
    global loadedDate
    global loadedDelta
    global loadedFactors
    global loadedArea
    global loadedDPI
    global loadedScale
    global loadedPRF
    global loadedBF
    global loadedSmooth
    global loadedProjection
    loadedLevel = config['presets'][f'{loadedPreset}']["level"]
    loadedDate = config['presets'][f'{loadedPreset}']["date"]
    loadedDelta = config['presets'][f'{loadedPreset}']["delta"]
    loadedFactors = config['presets'][f'{loadedPreset}']["factors"]
    loadedArea = config['presets'][f'{loadedPreset}']["area"]
    loadedDPI = config['presets'][f'{loadedPreset}']["dpi"]
    loadedScale = config['presets'][f'{loadedPreset}']["scale"]
    loadedPRF = config['presets'][f'{loadedPreset}']["prfactor"]
    loadedBF = config['presets'][f'{loadedPreset}']["barbfactor"]
    loadedSmooth = config['presets'][f'{loadedPreset}']["smoothing"]
    loadedProjection = config['presets'][f'{loadedPreset}']["projection"]
    
# Dump the loaded preset's contents
def paste():
    print(f"<loaded> Level: {loadedLevel}")
    print(f"<loaded> Date: {loadedDate}")
    print(f"<loaded> Delta: {loadedDelta}")
    print(f"<loaded> Factors: {loadedFactors}")
    print(f"<loaded> Area: {loadedArea}")
    print(f"<loaded> DPI: {loadedDPI}")
    print(f"<loaded> Scale: {loadedScale}")
    print(f"<loaded> PRF (Point Reduction Scale): {loadedPRF}")
    print(f"<loaded> BF (Barb Factor): {loadedBF}")
    print(f"<loaded> Smooth: {loadedSmooth}")
    print(f"<loaded> Projection: {loadedProjection}")
    
    
class Time(object):
    def __init__(self, loadedDate, level):
            currentTimeGridded = currentTime
            griddedHour = 0
            hour = 0
            if loadedDate == 'recent':
                if level == 'surface':
                    if currentTime.hour >= 21:
                        hour = 21
                        griddedHour = 12
                    elif currentTime.hour >= 18:
                        hours = 18
                        griddedHour = 12
                    elif currentTime.hour >= 15:
                        hour = 15
                        griddedHour = 6
                    elif currentTime.hour >= 12:
                        hour = 12
                        griddedHour = 6
                    elif currentTime.hour >= 9:
                        hour = 9
                        griddedHour = 0
                    elif currentTime.hour >= 6:
                        hour = 6
                        griddedHour = 0
                    elif currentTime.hour >= 3:
                        hour = 3
                        griddedHour = 18
                        currentTimeGridded = currentTime - timedelta(days=1)
                    else:
                        hour = 0
                        griddedHour = 18
                        currentTimeGridded = currentTime - timedelta(days=1)
                else:
                    if currentTime.hour >= 12:
                        hour = 12
                        griddedHour = hour
                    else:
                        hour = 0
                        griddedHour = hour
                year = currentTime.year
                month = currentTime.month
                day = currentTime.day
                inputTime = datetime(year, month, day, hour)
                inputTimeGridded = datetime(currentTimeGridded.year, currentTimeGridded.month, currentTimeGridded.day, griddedHour)
            else:
                parseDate1 = list(loadedDate.split(", "))
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
                if hour >= 18:
                    griddedHour = 18
                elif hour >= 12:
                    griddedHour = 12
                elif hour >= 6:
                    griddedHour = 6
                elif hour >= 0:
                    griddedHour = 0
                inputTimeGridded = datetime(year, month, day, griddedHour)
            daystamp = f"{year}-{inputTime.strftime('%m')}-{inputTime.strftime('%d')}"
            timestampNum = f"{year}-{inputTime.strftime('%m')}-{inputTime.strftime('%d')}-{inputTime.strftime('%H')}Z"
            timestampAlp = f"{inputTime.strftime('%b')} {day}, {year} - {hour}Z"
            
            self.T = inputTime
            self.GT = inputTimeGridded
            self.ds = daystamp
            self.tsnum = timestampNum
            self.tsalp = timestampAlp

            if (inputTime < datetime(1931, 1, 2)):
                sys.exit("<error> The date you entered is out of range!")
            elif (inputTime < datetime(1979, 1, 1)):
                print("<warning> The date you entered is out of range for gridded data.")
                gridRange = False
    
    def Time(self):
        return self.T
    
    def GriddedTime(self):
        return self.GT
    
    def Daystamp(self):
        return self.ds
    
    def NumericalTS(self):
        return self.tsnum
    
    def AlphanumericTS(self):
        return self.tsalp

def ParseTime(string, level):
    return Time(string, level)

def FromDatetime(datetimeObj, level):
        loadedTimeFormat = f"{datetimeObj.year}, {datetimeObj.month}, {datetimeObj.day}, {datetimeObj.hour}"
        newTime = ParseTime(loadedTimeFormat, level)
        return newTime

#class Map(object):
    #def __init__(self, dosave, assigned, titleOverride, (scaledDiff, scaledDiff), panel, heldTime, count, level)

    
# The meat of the program
def run(dosave, assigned, titleOverride, mode, **qrOverride):
    
    global loadedLevel
    global loadedDelta
    global loadedFactors
    rewind = 0
    # Handle quickrun overrides
    for k in qrOverride:
        if k == "date":
            heldTime = qrOverride[k]
        if k == "fcHour":
            loadedDelta = qrOverride[k]
        if k == "level":
            loadedLevel = qrOverride[k][0]
        if k == 'factors':
            loadedFactors = qrOverride[k]
        if k == "adtnlRwnd":
            rewind = qrOverride[k]
    
    loadedDelta = int(loadedDelta)
    
    # Level
    if loadedLevel != 'surface':
        level = int(loadedLevel)
    else:
        level = loadedLevel
        
    # Date
    if (quickRun != True) or ('date' not in qrOverride):
        heldTime = ParseTime(loadedDate, level)
    inputTime = heldTime.T
    inputTimeGridded = heldTime.GT
    daystamp = heldTime.ds
    timestampNum = heldTime.tsnum
    timestampAlp = heldTime.tsalp
    year = inputTime.year
        
    # Level-based formatting
    mslp_formatter = lambda v: format(v*10, '.0f')[-3:]

    if level != 'surface':
        if (level == 975) or (level == 850) or (level == 700):
            height_format = lambda v: format(v, '.0f')[1:]
            steps = 30
        elif level == 500:
            height_format = lambda v: format(v, '.0f')[:-1]
            steps = 60
        elif level == 300:
            height_format = lambda v: format(v, '.0f')[:-1]
            steps = 120
        elif level == 200:
            height_format = lambda v: format(v, '.0f')[1:-1]
            steps = 120
    

    # Data Acquisition
    inputTime = inputTime + timedelta(hours=-1*rewind)
    inputTime = inputTimeGridded + timedelta(hours=-1*rewind)
    plot_time = inputTimeGridded + timedelta(hours=loadedDelta)
    
    recentness = currentTime - inputTime
    if level == 'surface':
        if year < 2019:
            df = pd.read_csv(f'http://bergeron.valpo.edu/archive_surface_data/{inputTime:%Y}/{inputTime:%Y%m%d}_metar.csv', parse_dates=['date_time'], na_values=[-9999], low_memory=False)
            weather_format = 'present_weather'
        elif recentness < timedelta(days=14):
            #try:
            data = StringIO(urlopen('http://bergeron.valpo.edu/current_surface_data/'f'{inputTime:%Y%m%d%H}_sao.wmo').read().decode('utf-8', 'backslashreplace'))
            df = metar.parse_metar_file(data, year=inputTime.year, month=inputTime.month)
            weather_format = 'current_wx1_symbol'
            #except:
            #    Run(dosave, assigned, titleOverride, **{"adtnlRwnd":3})
        else:
            print("<error> The time you entered has no available surface data!")
            inputChain()
        df['tmpf'] = (df.air_temperature.values * units.degC).to('degF')
        df['dwpf'] = (df.dew_point_temperature.values * units.degC).to('degF')
    else:
        df = IAStateUpperAir.request_all_data(inputTime)
        df = add_station_lat_lon(df, 'station').dropna(subset=['latitude', 'longitude'])
        df = df[df.station != 'KVER'] # "central Missouri" station that shouldn't be there, due to faulty lat-lon data
        df['dewpoint_depression'] = df['temperature'] - df['dewpoint']
        
    if (recentness < timedelta(days=14)):
        #try:
        ds = xr.open_dataset('https://thredds.ucar.edu/thredds/dodsC/grib'f'/NCEP/GFS/Global_onedeg/GFS_Global_onedeg_{inputTimeGridded:%Y%m%d}_{inputTimeGridded:%H%M}.grib2').metpy.parse_cf()
        #except:
            #Run(dosave, assigned, titleOverride, **{"adtnlRwnd":6})
    elif (inputTime >= datetime(2004, 3, 2)):
        ds = xr.open_dataset('https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-g3-anl-files-old/'f'{inputTimeGridded:%Y%m/%Y%m%d}/gfsanl_3_{inputTimeGridded:%Y%m%d_%H}00_000.grb').metpy.parse_cf()
    elif (inputTime >= datetime(1979, 1, 1)):
        ds = xr.open_dataset('https://www.ncei.noaa.gov/thredds/dodsC/model-narr-a-files/'f'{inputTimeGridded:%Y%m/%Y%m%d}/narr-a_221_{inputTimeGridded:%Y%m%d_%H}00_000.grb').metpy.parse_cf()
        
    if level == 'surface':
        tmpk = ds.Temperature_height_above_ground.metpy.sel(vertical=2*units.m, time=plot_time)
        uwind = ds['u-component_of_wind_height_above_ground'].metpy.sel(vertical=10*units.m, time=plot_time)
        vwind = ds['v-component_of_wind_height_above_ground'].metpy.sel(vertical=10*units.m, time=plot_time)
        ds['wind_speed_height_above_ground'] = mpcalc.wind_speed(uwind, vwind)
    else:
        tmpk = ds.Temperature_isobaric.metpy.sel(vertical=level*units.hPa, time=plot_time)
        uwind = ds['u-component_of_wind_isobaric'].metpy.sel(vertical=level*units.hPa, time=plot_time)
        vwind = ds['v-component_of_wind_isobaric'].metpy.sel(vertical=level*units.hPa, time=plot_time)
        ds['wind_speed_isobaric'] = mpcalc.wind_speed(uwind, vwind)
    ds['relative_vorticity'] = mpcalc.vorticity(uwind, vwind)
    ds['temperature_advection'] = mpcalc.advection(tmpk, uwind, vwind)
    
    # Panel Preparation
    panel = declarative.MapPanel()
    panel.layout = (1, 1, 1)
    
    # Parse custom zoom feature
    simArea = loadedArea.replace("+", "")
    simArea = simArea.replace("-", "")
    if simArea in area_dictionary:
        splitArea = Counter(loadedArea)
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
        panel.area = f'{loadedArea}'

    # Figuring out the data display area
    areaZero = list(panel.area)
    areaScaleA = 1.1
    areaScaleB = 0.9
    if areaZero[0] < 0:
        areaZero[0] = 360 + (areaZero[0] * areaScaleA)
    if areaZero[1] < 0:
        areaZero[1] = 360 + (areaZero[1] * areaScaleB)
    areaZero[2] = areaZero[2] * areaScaleB
    areaZero[3] = areaZero[3] * areaScaleA
    latSlice = slice(areaZero[3], areaZero[2])
    lonSlice = slice(areaZero[0], areaZero[1])
    if (inputTime >= datetime(2004, 3, 2)):
        ds = ds.sel(lat=latSlice, lon=lonSlice)
    
    panel.layers = ['states', 'coastline', 'borders']
    
    # Parsing the panel.area into a list, and doing math on it.
    areaList = list(panel.area)
    areaMap = map(int, areaList)
    mapList = list(areaMap)
    diffLat = int(mapList[1])-int(mapList[0])
    diffLon = int(mapList[3])-int(mapList[2])
    avgDiff = ((diffLat + diffLon)//2)
    scaledDiff = math.floor(avgDiff*float(loadedScale))

    # Determining projection
    midLon = (mapList[1]+mapList[0])//2
    midLat = (mapList[3]+mapList[2])//2
    if loadedProjection == '' or loadedProjection == 'custom':
        projection = ccrs.LambertConformal(central_longitude = midLon, central_latitude = midLat)
    else:
        projection = loadedProjection
    panel.projection = projection
    
    
    # Factor Parsing
    plotslist = []
    factors = loadedFactors.split(", ")
        # Gridded
    if level != 'surface':
        if "temp_fill" in factors:
            temp_fill = declarative.FilledContourPlot()
            temp_fill.data = ds
            temp_fill.field = 'Temperature_isobaric'
            temp_fill.level = level * units.hPa
            temp_fill.time = plot_time
            temp_fill.contours = list(range(-100, 101, 1)) # rangeTL, rangeTH
            temp_fill.colormap = 'coolwarm'
            temp_fill.colorbar = 'horizontal'
            temp_fill.plot_units = 'degC'
            plotslist.append(temp_fill)
            
        if "wind_speed_fill" in factors:
            wind_speed_fill = declarative.FilledContourPlot()
            wind_speed_fill.data = ds
            wind_speed_fill.field = 'wind_speed_isobaric'
            wind_speed_fill.level = level * units.hPa
            wind_speed_fill.time = plot_time
            wind_speed_fill.contours = list(range(10, 201, 20))
            wind_speed_fill.colormap = 'BuPu'
            wind_speed_fill.colorbar = 'horizontal'
            wind_speed_fill.plot_units = 'knot'
            plotslist.append(wind_speed_fill)
            
        if "temp_advect_fill" in factors:
            temp_advect_fill = declarative.FilledContourPlot()
            temp_advect_fill.data = ds
            temp_advect_fill.field = 'temperature_advection'
            temp_advect_fill.level = None
            temp_advect_fill.time = None
            temp_advect_fill.contours = list(np.arange(-29, 30, 0.1))
            temp_advect_fill.colormap = 'bwr'
            temp_advect_fill.colorbar = 'horizontal'
            temp_advect_fill.scale = 3
            temp_advect_fill.plot_units = 'degC/hour'
            plotslist.append(temp_advect_fill)
            
        if "relative_vorticity_fill" in factors:
            relative_vorticity_fill = declarative.FilledContourPlot()
            relative_vorticity_fill.data = ds
            relative_vorticity_fill.field = 'relative_vorticity'
            relative_vorticity_fill.level = None
            relative_vorticity_fill.time = None
            relative_vorticity_fill.contours = list(range(-80, 81, 2))
            relative_vorticity_fill.colormap = 'PuOr_r'
            relative_vorticity_fill.colorbar = 'horizontal'
            relative_vorticity_fill.scale = 1e5
            plotslist.append(relative_vorticity_fill)
            
        if "absolute_vorticity_fill" in factors:
            absolute_vorticity_fill = declarative.FilledContourPlot()
            absolute_vorticity_fill.data = ds
            absolute_vorticity_fill.field = 'Absolute_vorticity_isobaric'
            absolute_vorticity_fill.level = level * units.hPa
            absolute_vorticity_fill.time = plot_time
            absolute_vorticity_fill.contours = list(range(-80, 81, 2))
            absolute_vorticity_fill.colormap = 'PuOr_r'
            absolute_vorticity_fill.colorbar = 'horizontal'
            absolute_vorticity_fill.scale = 1e5
            plotslist.append(absolute_vorticity_fill)
            
        if "height_contours" in factors:
            pressure_heights = declarative.ContourPlot()
            pressure_heights.data = ds
            pressure_heights.field = 'Geopotential_height_isobaric'
            pressure_heights.level = level * units.hPa
            pressure_heights.time = plot_time
            pressure_heights.contours = list(range(0, 12000, steps))
            pressure_heights.clabels = True
            pressure_heights.smooth_contour = int(loadedSmooth)
            plotslist.append(pressure_heights)
    
        if "temp_contours" in factors:
            temp_contours = declarative.ContourPlot()
            temp_contours.data = ds
            temp_contours.field = 'Temperature_isobaric'
            temp_contours.level = level * units.hPa
            temp_contours.time = plot_time
            temp_contours.contours = list(range(-100, 101, 5))
            temp_contours.linecolor = 'red'
            temp_contours.linestyle = 'dashed'
            temp_contours.clabels = True
            temp_contours.plot_units = 'degC'
            temp_contours.smooth_contour = int(loadedSmooth)
            plotslist.append(temp_contours)

        if "dew_contours" in factors:
            hPaLevel = level * units.hPa
            tmpIsoSel = ds['Temperature_isobaric'].metpy.sel(vertical=hPaLevel)
            rhIsoSel = ds['Relative_humidity_isobaric'].metpy.sel(vertical=hPaLevel)
            ds['Dewpoint_isobaric'] = mpcalc.dewpoint_from_relative_humidity(tmpIsoSel, rhIsoSel)
            dew_contours = declarative.ContourPlot()
            dew_contours.data = ds
            dew_contours.field = 'Dewpoint_isobaric'
            dew_contours.level = None
            dew_contours.time = plot_time
            dew_contours.contours = list(range(-100, 101, 5))
            dew_contours.linecolor = 'green'
            dew_contours.linestyle = 'dashed'
            dew_contours.clabels = True
            #dew_contours.plot_units = 'degC'
            dew_contours.smooth_contours = int(loadedSmooth)
            plotslist.append(dew_contours)
        
        if "gridded_barbs" in factors:
            barbs = declarative.BarbPlot()
            barbs.data = ds
            barbs.time = plot_time
            barbs.field = ['u-component_of_wind_isobaric', 'v-component_of_wind_isobaric']
            barbs.level = level * units.hPa
            barbs.skip = (int(loadedBF), int(loadedBF))
            barbs.plot_units = 'knot'
            plotslist.append(barbs)
            
    else:
        if "temp_fill" in factors:
            temp_fill = declarative.FilledContourPlot()
            temp_fill.data = ds
            temp_fill.field = 'Temperature_height_above_ground'
            temp_fill.level = 2 * units.m
            temp_fill.time = plot_time
            temp_fill.contours = list(range(-68, 133, 2)) # rangeTL_F, rangeTH_F
            temp_fill.colormap = 'coolwarm'
            temp_fill.colorbar = 'horizontal'
            temp_fill.plot_units = 'degF'
            plotslist.append(temp_fill)
            
        if "wind_speed_fill" in factors:
            wind_speed_fill = declarative.FilledContourPlot()
            wind_speed_fill.data = ds
            wind_speed_fill.field = 'wind_speed_height_above_ground'
            wind_speed_fill.level = 10 * units.m
            wind_speed_fill.time = plot_time
            wind_speed_fill.contours = list(range(10, 201, 20))
            wind_speed_fill.colormap = 'BuPu'
            wind_speed_fill.colorbar = 'horizontal'
            wind_speed_fill.plot_units = 'knot'
            plotslist.append(wind_speed_fill)
            
        if "temp_advect_fill" in factors:
            temp_advect_fill = declarative.FilledContourPlot()
            temp_advect_fill.data = ds
            temp_advect_fill.field = 'temperature_advection'
            temp_advect_fill.level = None
            temp_advect_fill.time = None
            temp_advect_fill.contours = list(np.arange(-29, 30, 0.1))
            temp_advect_fill.colormap = 'bwr'
            temp_advect_fill.colorbar = 'horizontal'
            temp_advect_fill.scale = 3
            temp_advect_fill.plot_units = 'degC/hour'
            plotslist.append(temp_advect_fill)
            
        if "relative_vorticity_fill" in factors:
            relative_vorticity_fill = declarative.FilledContourPlot()
            relative_vorticity_fill.data = ds
            relative_vorticity_fill.field = 'relative_vorticity'
            relative_vorticity_fill.level = None
            relative_vorticity_fill.time = None
            relative_vorticity_fill.contours = list(range(-40, 41, 2))
            relative_vorticity_fill.colormap = 'PuOr_r'
            relative_vorticity_fill.colorbar = 'horizontal'
            relative_vorticity_fill.scale = 1e5
            plotslist.append(relative_vorticity_fill)

        if "pressure_contours" in factors:
            pressure = declarative.ContourPlot()
            pressure.data = ds
            pressure.field = 'Pressure_reduced_to_MSL_msl'
            pressure.level = None
            pressure.time = plot_time
            pressure.contours = list(range(0, 2000, 4))
            pressure.clabels = True
            pressure.plot_units = 'hPa'
            pressure.smooth_contour = int(loadedSmooth)
            plotslist.append(pressure)
            
        if "temp_contours" in factors:
            temp_contours = declarative.ContourPlot()
            temp_contours.data = ds
            temp_contours.field = 'Temperature_height_above_ground'
            temp_contours.level = 2 * units.m
            temp_contours.time = plot_time
            temp_contours.contours = list(range(-100, 101, 10))
            temp_contours.linecolor = 'red'
            temp_contours.linestyle = 'dashed'
            temp_contours.clabels = True
            temp_contours.plot_units = 'degF'
            temp_contours.smooth_contour = int(loadedSmooth)
            plotslist.append(temp_contours)
            
        if "dew_contours" in factors:
            dew_contours = declarative.ContourPlot()
            dew_contours.data = ds
            dew_contours.field = 'Dewpoint_temperature_height_above_ground'
            dew_contours.level = 2 * units.m
            dew_contours.time = plot_time
            dew_contours.contours = list(range(-100, 101, 10))
            dew_contours.linecolor = 'green'
            dew_contours.linestyle = 'dashed'
            dew_contours.clabels = True
            dew_contours.plot_units = 'degF'
            dew_contours.smooth_contour = int(loadedSmooth)
            plotslist.append(dew_contours)
            
        if "gridded_barbs" in factors:
            barbs = declarative.BarbPlot()
            barbs.data = ds
            barbs.time = plot_time
            barbs.field = ['u-component_of_wind_height_above_ground', 'v-component_of_wind_height_above_ground']
            barbs.level = 10 * units.m
            barbs.skip = (int(loadedBF), int(loadedBF))
            barbs.plot_units = 'knot'
            plotslist.append(barbs)
            
                    # Observations
    obsfields = []
    obscolors = []
    obslocations = []
    obsformats = []
    
    obs = declarative.PlotObs()
    obs.data = df
    obs.time = inputTime
    
    if "temperature" in factors:
        if level == 'surface':
            obsfields.append('tmpf')
        else:
            obsfields.append('temperature')
        obscolors.append('crimson')
        obslocations.append('NW')
        obsformats.append(None)
    if "dewpoint" in factors:
        if level == 'surface':
            obsfields.append('dwpf')
        else:
            obsfields.append('dewpoint')
        obscolors.append('green')
        obslocations.append('SW')
        obsformats.append(None)
    elif "dewpoint_depression" in factors:
        obsfields.append('dewpoint_depression')
        obscolors.append('green')
        obslocations.append('SW')
        obsformats.append(height_format)
    if "height" in factors:
        obsfields.append('height')
        obscolors.append('darkslategrey')
        obslocations.append('NE')
        obsformats.append(height_format)
    if "pressure" in factors:
        obsfields.append('air_pressure_at_sea_level')
        obscolors.append('darkslategrey')
        obslocations.append('NE')
        obsformats.append(mslp_formatter)
    if 'current_weather' in factors:
        obsfields.append(f'{weather_format}')
        obscolors.append('indigo')
        obslocations.append('W')
        obsformats.append('current_weather')
    if "barbs" in factors:
        if level == 'surface':
            obs.vector_field = ['eastward_wind', 'northward_wind']
        else:
            obs.vector_field = ['u_wind', 'v_wind']
    if "cloud_coverage" in factors:
        obsfields.append('cloud_coverage')
        obscolors.append('black')
        obslocations.append('C')
        obsformats.append('sky_cover')
        
    if ("temperature" in factors) or ("dewpoint" in factors) or ("dewpoint_depression" in factors) or ("height" in factors) or ("pressure" in factors) or ('current_weather' in factors) or ("barbs" in factors) or ("cloud_coverage" in factors):
        plotslist.append(obs)
    
    obs.fields = obsfields
    obs.colors = obscolors
    obs.formats = obsformats
    obs.locations = obslocations
    obs.reduce_points = float(loadedPRF)
    
    if level == 'surface':
        obs.level = None
        obs.time_window = timedelta(minutes=15)
    else:
        obs.level = level * units.hPa
        
        
    conTitle = "Contour Map"
    sConTitle = "Surface Contour Map"
    obsTitle = "Map"
    sObsTitle = "Surface Map"
    
    if titleOverride != '':
        conTitle = titleOverride
        sConTitle = titleOverride
        obsTitle = titleOverride
        sObsTitle = titleOverride
        
    panel.plots = plotslist
    count = len(plotslist)
    if count > 1:
        if level == 'surface':
            panel.title = f'Bailey, Sam - {loadedArea} {sConTitle} {timestampAlp}, {loadedDelta} Hour Forecast'
        else:
            panel.title = f'Bailey, Sam - {loadedArea} {level}mb {conTitle} {timestampAlp}, {loadedDelta} Hour Forecast'
    else:
        if level == 'surface':
            panel.title = f'Bailey, Sam - {loadedArea} {sObsTitle} {timestampAlp}'
        else:
            panel.title = f'Bailey, Sam - {loadedArea} {level}mb {obsTitle} {timestampAlp}'
            
    #if mode == 0:
    MapSave(dosave, assigned, titleOverride, (scaledDiff, scaledDiff), panel, heldTime, count, level)
    #elif mode == 1:
        #Multi-panel feed
    
    
def MapSave(dosave, assigned, titleOverride, panelSize, panel, plotTime, count, level):
    
    conTitle = "Contour Map"
    sConTitle = "Surface Contour Map"
    obsTitle = "Map"
    sObsTitle = "Surface Map"
    
    if titleOverride != '':
        conTitle = titleOverride
        sConTitle = titleOverride
        obsTitle = titleOverride
        sObsTitle = titleOverride
    
    daystamp = plotTime.ds
    timestampNum = plotTime.tsnum
    timestampAlp = plotTime.tsalp
    
    pc = declarative.PanelContainer()
    pc.size = panelSize
    pc.panels = [panel]
    # Saving the map
    if assigned:
        saveLocale = 'Assignment_Maps'
    else:
        saveLocale = 'Test_Maps'

    OldDir = os.path.isdir(f'../Maps/{saveLocale}/{daystamp}')

    if dosave:
        if OldDir == False:
            os.mkdir(f'../Maps/{saveLocale}/{daystamp}')
        if (count > 1):
            if level != 'surface':
                pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedDelta:02d}H, {loadedArea} {level}mb {conTitle}, {loadedDPI} DPI - Bailey, Sam.png', dpi=int(loadedDPI), bbox_inches='tight')
                save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedDelta:02d}H, {loadedArea} {level}mb {conTitle}, {loadedDPI} DPI - Bailey, Sam.png')
                if noShow == False:
                    save.show()
            else:
                pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedDelta:02d}H, {loadedArea} {sConTitle}, {loadedDPI} DPI - Bailey, Sam.png', dpi=int(loadedDPI), bbox_inches='tight')
                save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedDelta:02d}H, {loadedArea} {sConTitle}, {loadedDPI} DPI - Bailey, Sam.png')
                if noShow == False:
                    save.show()
        else:
            if level != 'surface':
                pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedArea} {level}mb {obsTitle}, {loadedDPI} DPI - Bailey, Sam.png', dpi=int(loadedDPI), bbox_inches='tight')
                save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedArea} {level}mb {obsTitle}, {loadedDPI} DPI - Bailey, Sam.png')
                if noShow == False:
                    save.show()
            else:
                pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedArea} {sObsTitle}, {loadedDPI} DPI - Bailey, Sam.png', dpi=int(loadedDPI), bbox_inches='tight')
                save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedArea} {sObsTitle}, {loadedDPI} DPI - Bailey, Sam.png')
                if noShow == False:
                    save.show()
        print("<run> Map successfully saved!")
    else:
        pc.save(f'temp.png', dpi=int(loadedDPI), bbox_inches='tight')
        save = Image.open(f'temp.png')
        if noShow == False:
            save.show()
        os.remove(f'temp.png')
    
    if quickRun != True:
        inputChain()

        
        
#def MultiSave:
# --- End Definitions ---



# Init
area_dictionary = dict(config['areas'])
area_dictionary = {k: tuple(map(float, v.split(", "))) for k, v in area_dictionary.items()}

possibleFactors = ["loadedLevel", "loadedDate", "loadedDelta", "loadedFactors", "loadedArea", "loadedDPI", "loadedScale", "loadedPRF", "loadedBF", "loadedSmooth", "loadedProjection"]

global quickRun
global noShow
quickRun = False
noShow = False

# Check for quickrun commands
if len(sys.argv) > 1:
    noShow = False
    dosave = False
    assigned = False
    allLevels = False
    allevels = ["surface", 850, 500, 300, 200]
    levels = []
    fchours = [0]
    dates = [0]
    jump = 6
    overrides = {}
    overrides.update({"fcloop":0})
    overrides.update({"dloop":0})
    overrides.update({"fcHour":0})
    setTime()
    if sys.argv[1] == "--quickrun":
        presetLoad('default')
        overrides.update({"level":"surface"})
        basedate = ParseTime("recent", "surface").T
        quickRun = True
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--preset":
                presetLoad(f'{sys.argv[i + 1]}')
            if sys.argv[i] == "-s":
                dosave = True
            if sys.argv[i] == "-a":
                assigned = True
            if sys.argv[i] == "--fchour":
                overrides.update({"fcHour":f"{sys.argv[i + 1]}"})
            if sys.argv[i] == "--level":
                levels.append(sys.argv[i + 1].replace('"', '').split(', '))
            if sys.argv[i] == "-allevels":
                levels = allevels
            if sys.argv[i] == "--fcloop":
                overrides.update({"fcloop":int(sys.argv[i + 1])})
            if sys.argv[i] == "--dloop":
                overrides.update({"dloop":int(sys.argv[i + 1])})
            if sys.argv[i] == "--jump":
                jump = sys.argv[i + 1]
            if sys.argv[i] == "-ns":
                noShow = True
            if sys.argv[i] == "--date":
                basedate = ParseTime(sys.argv[i + 1], overrides['level']).T
            if sys.argv[i] == "--factors":
                overrides.update({"factors":sys.argv[i + 1].replace('"', '')})
            i += 1
        
        while overrides['fcloop'] >= 1:
            fchours.append(overrides['fcloop'] * 6)
            overrides.update({"fcloop":(overrides['fcloop'] - 1)})
            
        while overrides['dloop'] >= 1:
            dates.append(overrides['dloop'] * jump)
            overrides.update({"dloop":(overrides['dloop'] - 1)})
            
        while overrides['dloop'] <= 1:
            dates.append(overrides['dloop'] * jump)
            overrides.update({"dloop":(overrides['dloop'] + 1)})
        
        for fch in fchours:
            for dt in dates:
                for lvl in levels:
                    overrides.update({'fcHour':fch})
                    overrides.update({'level':lvl})
                    overrides.update({'date':FromDatetime((basedate + timedelta(hours=dt)), overrides['level'])})
                    run(dosave, assigned, '', 0, **overrides)
                    
    elif sys.argv[1] == "-help":
        for line in list(range(60, 136, 1)):
            if line != 135:
                print(manual[line], end='')
            else:
                print(manual[line])
        
    sys.exit()
else:
    # Version handler
    print(f"<menu> You are using AMGP version {version}")
    cfgver = config["config_ver"].split('.')
    amgpver = version.split('.')
    if config["config_ver"] != version:
        if cfgver[0] > amgpver[0]:
            sys.exit(f"<error> Your installed AMGP version is out of date! Config version {config['config_ver']} found.")
        elif cfgver[0] < amgpver[0]:
            sys.exit(f"<error> The config we found is out of date! Config version {config['config_ver']} found.")
            # attempt to update the config in the future
        elif cfgver[1] > amgpver[1]:
            sys.exit(f"<error> Your installed AMGP version is out of date! Config version {config['config_ver']} found.")
        elif cfgver[1] < amgpver[1]:
            print(f"<warning> The loaded config file is of an earlier version ({config['config_ver']}), consider updating it.")
        else:
            print(f"<warning> The loaded config file we found is of a different compatible version version ({config['config_ver']}).")
    print("<menu> Config loaded.")

    # Pre-running
    getTime()
    presetLoad('default')
    paste()

    inputChain()