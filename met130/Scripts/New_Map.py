################################################
#                                              #
#       Automated Map Generation Program       #
#                                              #
#            Author: Sam Bailey                #
#        Last Revised: Mar 10, 2022            #
#                Version 0.1                   #
#                                              #
#          Created on Mar 09, 2022             #
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
import metpy.calc as mpcalc
import xarray as xr
import pandas as pd
from collections import Counter
import math
import os
import sys
from PIL import Image
import json

version = 0.1

# Opening the config file
if os.path.isfile("config.json"):
    with open("config.json", "r") as cfg:
        config = json.load(cfg)

print(f"<menu> You are using AMGP version {version}.")
if float(config["config_ver"]) != version:
    print(f"<warning> The loaded config file we found is of a different version ({config['config_ver']}).")
else:
    print("<menu> Config loaded.")
    
# Retrieving and setting the current UTC time
currentTime = datetime.utcnow()
print(f"<menu> It is currently {currentTime}Z")

area_dictionary = dict(config['areas'])
area_dictionary = {k: tuple(map(float, v.split(", "))) for k, v in area_dictionary.items()}

possibleFactors = ["loadedLevel", "loadedDate", "loadedDelta", "loadedFactors", "loadedArea", "loadedDPI", "loadedScale", "loadedPRF", "loadedBF", "loadedSmooth", "loadedProjection"]

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
    
    print("<menu> Input commands. For a list of commands, type 'list'.")
    comm = input("<input> ")
    
    command = comm.split(" ")
    
    if command[0] == "list":
        print("<list> Type 'preset {name}' to load a map preset.")
        print("<list> Type 'preset list' to list available presets.")
        print("<list> Type 'factors' to list accepted map factors.")
        print("<list> Type 'paste' to see the currently loaded values.")
        print("<list> Type 'edit {parameter} {value}' to edit a loaded parameter.")
        print("<list> Type 'save {preset name}' to save the current settings as a preset.")
        print("<list> Type 'run' to run with the current settings.")
        print("<list> Type 'quit' to exit without running.")
        inputChain()
    
    if command[0] == 'preset':
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
        print("<factors> 'gridded_barbs' - Gridded winds")
        print("<factors> 'pressure_contours' - Gridded pressure contours (surface only)")
        print("<factors> 'dew_contours' - Gridded dewpoint contours (surface only)")
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
        save('prev')
        print("<run> Previous settings saved.")
        run(S, A)
    elif command[0] == 'quit':
        sys.exit("<quit> The process was terminated.")
    else:
        print("<error> That is not a valid command!")
        inputChain()
        
def save(name):
    namei = {"level":f"{loadedLevel}","date":f"{loadedDate}","delta":f"{loadedDelta}","factors":f"{loadedFactors}","area":f"{loadedArea}","dpi":f"{loadedDPI}","scale":f"{loadedScale}","prfactor":f"{loadedPRF}","barbfactor":f"{loadedBF}","smoothing":f"{loadedSmooth}","projection":f"{loadedProjection}"}
    config['presets'][f'{name}'] = namei
    with open("config.json", "w") as J:
        json.dump(config, J)

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

def run(dosave, assigned):
    
    # Level
    if loadedLevel != 'surface':
        level = int(loadedLevel)
    else:
        level = loadedLevel
        
    # Date
    currentTimeGridded = currentTime
    griddedHour = 0
    if loadedDate == 'recent':
        if level == 'surface':
            if currentTime.hour >= 21:
                hour = 21
                griddedHour = 12
            elif currentTime.hour >= 18:
                hour = 18
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
            else:
                hour = 0
        year = currentTime.year
        month = currentTime.month
        day = currentTime.day
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
    inputTimeGridded = datetime(currentTimeGridded.year, currentTimeGridded.month, currentTimeGridded.day, griddedHour)
    daystamp = f"{year}-{inputTime.strftime('%m')}-{inputTime.strftime('%d')}"
    timestampNum = f"{year}-{inputTime.strftime('%m')}-{inputTime.strftime('%d')}-{inputTime.strftime('%H')}Z"
    timestampAlp = f"{inputTime.strftime('%b')} {day}, {year} - {hour}Z"
    
    if (inputTime < datetime(1931, 1, 2)):
        sys.exit("<error> The date you entered is out of range!")
    elif (inputTime < datetime(1979, 1, 1)):
        print("<warning> The date you entered is out of range for gridded data.")
        gridRange = False
        
    # Level-based formatting
    mslp_formatter = lambda v: format(v*10, '.0f')[-3:]

    if level != 'surface':
        if (level == 975) or (level == 850) or (level == 700):
            height_format = lambda v: format(v, '.0f')[1:]
        elif (level == 500) or (level == 300):
            height_format = lambda v: format(v, '.0f')[:-1]
        elif level == 200:
            height_format = lambda v: format(v, '.0f')[1:-1]
    
    if level != 'surface':
        if (level == 975) or (level == 850) or (level == 700):
            steps = 30
        elif (level == 500):
            steps = 60
        elif (level == 300) or (level == 200):
            steps = 120
    
    # Data Acquisition
    recentness = currentTime - inputTime
    if level == 'surface':
        if year < 2019:
            df = pd.read_csv(f'http://bergeron.valpo.edu/archive_surface_data/{inputTime:%Y}/{inputTime:%Y%m%d}_metar.csv', parse_dates=['date_time'], na_values=[-9999], low_memory=False)
            weather_format = 'present_weather'
        elif recentness < timedelta(days=14):
            data = StringIO(urlopen('http://bergeron.valpo.edu/current_surface_data/'f'{inputTime:%Y%m%d%H}_sao.wmo').read().decode('utf-8', 'backslashreplace'))
            df = metar.parse_metar_file(data, year=inputTime.year, month=inputTime.month)
            weather_format = 'current_wx1_symbol'
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
        ds = xr.open_dataset('https://thredds.ucar.edu/thredds/dodsC/grib'f'/NCEP/GFS/Global_onedeg/GFS_Global_onedeg_{inputTimeGridded:%Y%m%d}_{inputTimeGridded:%H%M}.grib2').metpy.parse_cf()
    elif (inputTime >= datetime(2004, 3, 2)):
        ds = xr.open_dataset('https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-g3-anl-files-old/'f'{inputTimeGridded:%Y%m/%Y%m%d}/gfsanl_3_{inputTimeGridded:%Y%m%d_%H}00_000.grb').metpy.parse_cf()
    elif (inputTime >= datetime(1979, 1, 1)):
        ds = xr.open_dataset('https://www.ncei.noaa.gov/thredds/dodsC/model-narr-a-files/'f'{inputTimeGridded:%Y%m/%Y%m%d}/narr-a_221_{inputTimeGridded:%Y%m%d_%H}00_000.grb').metpy.parse_cf()
        
    plot_time = inputTime + timedelta(hours=int(loadedDelta))
    
    # Panel Preparation
    panel = declarative.MapPanel()
    panel.layout = (1, 1, 1)
    simArea = loadedArea.replace("+", "")
    simArea = simArea.replace("-", "")
    if simArea in area_dictionary:
        # Parse custom zoom feature
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
        # Observations
    obsfields = []
    obscolors = []
    obslocations = []
    obsformats = []
    
    obs = declarative.PlotObs()
    obs.data = df
    obs.time = inputTime
    
    factors = loadedFactors.split(", ")
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
        
        # Gridded
    if level != 'surface':
        if "height_contours" in factors:
            pressure_heights = declarative.ContourPlot()
            pressure_heights.data = ds
            pressure_heights.field = 'Geopotential_height_isobaric'
            pressure_heights.level = level * units.hPa
            pressure_heights.time = plot_time
            pressure_heights.contours = list(range(0, 12000, steps))
            pressure_heights.clabels = True
            pressure_heights.smooth_contour = loadedSmooth
            plotslist.append(pressure_heights)
    
        if "temp_contours" in factors:
            temp_contours = declarative.ContourPlot()
            temp_contours.data = ds
            temp_contours.field = 'Temperature_isobaric'
            temp_contours.level = level * units.hPa
            temp_contours.time = plot_time
            temp_contours.contours = list(range(-100, 100, 5))
            temp_contours.linecolor = 'red'
            temp_contours.linestyle = 'dashed'
            temp_contours.clabels = True
            temp_contours.plot_units = 'degC'
            temp_contours.smooth_contour = loadedSmooth
            plotslist.append(temp_contours)

#        Currently, this doesn't work.
#        if "dew_contours" in factors:
#            hPaLevel = level * units.hPa
#            tmpIsoSel = ds['Temperature_isobaric'].metpy.sel(vertical=hPaLevel)
#            rhIsoSel = ds['Relative_humidity_isobaric'].metpy.sel(vertical=hPaLevel)
#            ds['Dewpoint_isobaric'] = mpcalc.dewpoint_from_relative_humidity(tmpIsoSel, rhIsoSel)
#            dew_contours = declarative.ContourPlot()
#            dew_contours.data = ds
#            dew_contours.field = 'Dewpoint_isobaric'
#            dew_contours.level = level * units.hPa
#            dew_contours.time = plot_time
#            dew_contours.contours = list(range(-100, 100, 5))
#            dew_contours.linecolor = 'green'
#            dew_contours.linestyle = 'dashed'
#            dew_contours.clabels = True
#            dew_contours.plot_units = 'degC'
#            dew_contours.smooth_contour = loadedSmooth
#            plotslist.append(dew_contours)
        
        if "temp_fill" in factors:
            temp_fill = declarative.FilledContourPlot()
            temp_fill.data = ds
            temp_fill.field = 'Temperature_isobaric'
            temp_fill.level = level * units.hPa
            temp_fill.time = plot_time
            temp_fill.contours = list(range(-100, 100, 1)) # rangeTL, rangeTH
            temp_fill.colormap = 'coolwarm'
            temp_fill.colorbar = 'horizontal'
            temp_fill.plot_units = 'degC'
            plotslist.append(temp_fill)
        
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
        if "pressure_contours" in factors:
            pressure = declarative.ContourPlot()
            pressure.data = ds
            pressure.field = 'Pressure_reduced_to_MSL_msl'
            pressure.level = None
            pressure.time = plot_time
            pressure.contours = list(range(0, 2000, 4))
            pressure.clabels = True
            pressure.plot_units = 'hPa'
            pressure.smooth_contour = loadedSmooth
            plotslist.append(pressure)
        
        if "temp_fill" in factors:
            temp_fill = declarative.FilledContourPlot()
            temp_fill.data = ds
            temp_fill.field = 'Temperature_height_above_ground'
            temp_fill.level = 2 * units.m
            temp_fill.time = plot_time
            temp_fill.contours = list(range(-68, 132, 2)) # rangeTL_F, rangeTH_F
            temp_fill.colormap = 'coolwarm'
            temp_fill.colorbar = 'horizontal'
            temp_fill.plot_units = 'degF'
            plotslist.append(temp_fill)
            
        if "temp_contours" in factors:
            temp_contours = declarative.ContourPlot()
            temp_contours.data = ds
            temp_contours.field = 'Temperature_height_above_ground'
            temp_contours.level = 2 * units.m
            temp_contours.time = plot_time
            temp_contours.contours = list(range(-100, 100, 10))
            temp_contours.linecolor = 'red'
            temp_contours.linestyle = 'dashed'
            temp_contours.clabels = True
            temp_contours.plot_units = 'degF'
            temp_contours.smooth_contour = loadedSmooth
            plotslist.append(temp_contours)
            
        if "dew_contours" in factors:
            dew_contours = declarative.ContourPlot()
            dew_contours.data = ds
            dew_contours.field = 'Dewpoint_temperature_height_above_ground'
            dew_contours.level = 2 * units.m
            dew_contours.time = plot_time
            dew_contours.contours = list(range(-100, 100, 10))
            dew_contours.linecolor = 'green'
            dew_contours.linestyle = 'dashed'
            dew_contours.clabels = True
            dew_contours.plot_units = 'degF'
            dew_contours.smooth_contour = loadedSmooth
            plotslist.append(dew_contours)
            
        if "gridded_barbs" in factors:
            barbs = declarative.BarbPlot()
            barbs.data = ds
            barbs.time = plot_time
            barbs.field = ['u-component_of_wind_height_above_ground', 'v-component_of_wind_height_above_ground']
            barbs.level = 10 * units.m
            barbs.skip = (int(barbfactor), int(barbfactor))
            barbs.plot_units = 'knot'
            plotslist.append(barbs)
        
    panel.plots = plotslist
    count = len(plotslist)
    if count > 1:
        if level == 'surface':
            panel.title = f'Bailey, Sam - {loadedArea} Surface Contour Map {timestampAlp}, {loadedDelta} Hour Forecast'
        else:
            panel.title = f'Bailey, Sam - {loadedArea} {level}mb Contour Map {timestampAlp}, {loadedDelta} Hour Forecast'
    else:
        if level == 'surface':
            panel.title = f'Bailey, Sam - {loadedArea} Surface Map {timestampAlp}'
        else:
            panel.title = f'Bailey, Sam - {loadedArea} {level}mb Map {timestampAlp}'

    pc = declarative.PanelContainer()
    pc.size = (scaledDiff, scaledDiff)
    pc.panels = [panel]
    
    
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
                pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedDelta}H, {loadedArea} {level}mb Contour Map, {loadedDPI} DPI - Bailey, Sam.png', dpi=int(loadedDPI), bbox_inches='tight')
                save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedDelta}H, {loadedArea} {level}mb Contour Map, {loadedDPI} DPI - Bailey, Sam.png')
                save.show()
            else:
                pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedDelta}H, {loadedArea} Surface Contour Map, {loadedDPI} DPI - Bailey, Sam.png', dpi=int(loadedDPI), bbox_inches='tight')
                save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedDelta}H, {loadedArea} Surface Contour Map, {loadedDPI} DPI - Bailey, Sam.png')
                save.show()
        else:
            if level != 'surface':
                pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedArea} {level}mb Map, {loadedDPI} DPI - Bailey, Sam.png', dpi=int(loadedDPI), bbox_inches='tight')
                save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedArea} {level}mb Map, {loadedDPI} DPI - Bailey, Sam.png')
                save.show()
            else:
                pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedArea} Surface Map, {loadedDPI} DPI - Bailey, Sam.png', dpi=int(loadedDPI), bbox_inches='tight')
                save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {loadedArea} Surface Map, {loadedDPI} DPI - Bailey, Sam.png')
                save.show()
        print("<run> Map successfully saved!")
    else:
        pc.save(f'temp.png', dpi=dpiSet, bbox_inches='tight')
        save = Image.open(f'temp.png')
        save.show()
        os.remove(f'temp.png')
    
    inputChain()


# Pre-running
presetLoad('default')
paste()

inputChain()