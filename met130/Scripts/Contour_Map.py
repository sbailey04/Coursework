################################################
#                                              #
#    Automated Contour Map Generator Script    #
#                                              #
#            Author: Sam Bailey                #
#        Last Revised: Mar 02, 2022            #
#                                              #
#          Created on Feb 22, 2022             #
#                                              #
################################################

from datetime import datetime, timedelta
from metpy.plots import declarative
from metpy.units import units
import xarray as xr
import cartopy.crs as ccrs
from collections import Counter
import math
import os
from PIL import Image


# Retrieving and setting the current UTC time
currentTime = datetime.utcnow()
print(f"> It is currently {currentTime}Z")


# User input
prevInput = input("> Would you like to use the previous entry [y/n, default 'n']: ")
if prevInput == 'y':
    prevCon = open('prevCon.txt', 'r')
    prevConStored = prevCon.readlines()
    count = 0
    prevConList = []
    for line in prevConStored:
        prevConList.append(line.strip())
        count += 1
    levelInputPrev = prevConList[0]
    inputDatePrev = prevConList[1]
    dTimePrev = prevConList[2]
    factorsPrev = prevConList[3]
    areaPrev = prevConList[4]
    dpiSet0Prev = prevConList[5]
    scale0Prev = prevConList[6]
    barbfactor0Prev = prevConList[7]
    smoothingPrev = prevConList[8]
    projectionInputPrev = prevConList[9]
    

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
    if currentTime.hour >= 18:
        hour = 12
    elif currentTime.hour >= 12:
        hour = 6
    elif currentTime.hour >= 6:
        hour = 0
    else:
        hour = 18
        currentTime = currentTime - timedelta(days=1)
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

if prevInput == 'y':
    dTime = input(f"> Input the time delta [default 0, Prev: {dTimePrev}]: ")
else:
    dTime = input("> Input the time delta [default 0]: ")
if (prevInput == 'y') and (dTime == ''):
    dTime = dTimePrev
if (dTime == '') or (dTime == 'default'):
    dTime = 0
else:
    dTime = int(dTime)
    
print('> "Supported inputs are:"')
print('> "pressure" (S)')
print('> "pressure_heights" (!S)')
print('> "temp_contours"')
print('> "temp_fill"')
print('> "barbs"')
if prevInput == 'y':
    factors = input(f"> Select the map objects you would like to include, separated by ', ' [Prev: {factorsPrev}]: ")
else:
    factors = input("> Select the map objects you would like to include, separated by ', ': ")
if (prevInput == 'y') and (factors == ''):
    factors = factorsPrev
factorsPart = factors.split(', ')
plots_list = []


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
if (scale0 == '') or (scale0 == 'default'):
    scale = 1.3
else:
    scale = float(scale0)

if "barbs" in factorsPart:
    if prevInput == 'y':
        barbfactor0 = input(f"> Enter the barb reduction factor [default 3, Prev: {barbfactor0Prev}]: ")
    else:
        barbfactor0 = input("> Enter the barb reduction factor [default 3]: ")
    if (prevInput == 'y') and (barbfactor0 == ''):
        barbfactor0 == barbfactor0Prev
    if (barbfactor0 == '') or (barbfactor0 == 'default'):
        barbfactor = 3
    else:
        barbfactor = int(barbfactor0)

if ("temp_contours" in factorsPart) or ("pressure" in factorsPart) or ("pressure_heights" in factorsPart):
    if prevInput == 'y':
        smoothing = input(f"> Enter the contour smoothing factor [default 0, Prev: {smoothingPrev}]: ")
    else:
        smoothing = input("> Enter the contour smoothing factor [default 0]: ")
    if (prevInput == 'y') and (smoothing == ''):
        smoothing = smoothingPrev
    if (smoothing == '') or (smoothing == 'default'):
        smoothing = 0
    else:
        smoothing = int(smoothing)

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
if os.path.isfile("prevCon.txt"):
    os.remove("prevCon.txt")
with open("prevCon.txt", "x") as prev:
    W = [f'{levelInput}\n', f'{inputDate}\n', f'{dTime}\n', f'{factors}\n', f'{area}\n', f'{dpiSet0}\n', f'{scale0}\n', f'{barbfactor0}\n', f'{smoothing}\n', f'{projectionInput}\n']
    prev.writelines(W)


ds = xr.open_dataset('https://thredds.ucar.edu/thredds/dodsC/grib'
                     f'/NCEP/GFS/Global_onedeg/GFS_Global_onedeg_{inputTime:%Y%m%d}_{inputTime:%H%M}.grib2')


# Set the plot time with forecast hours
plot_time = inputTime + timedelta(hours=dTime)

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

areaZero = list(panel.area)
areaScaleA = 1.1
areaScaleB = 0.9
if areaZero[0] < 0:
    areaZero[0] = 360 + (areaZero[0] * areaScaleA)
if areaZero[1] < 0:
    areaZero[1] = 360 + (areaZero[1] * areaScaleB)
areaZero[2] = areaZero[2] * areaScaleB
areaZero[3] = areaZero[3] * areaScaleA

# Subset data to be just over the U.S. for plotting purposes
ds = ds.sel(lat=slice(areaZero[3], areaZero[2]), lon=slice(areaZero[0], areaZero[1]))

#minTemp = min(list(map(ds.Temperature_isobaric.values, int)))
#maxTemp = max(list(map(ds.Temperature_isobaric.values, int)))
#minDiffT = abs(0 - minTemp)
#maxDiffT = abs(maxTemp - 0)
#diffT = max(list(madDiffT, minDiffT))
#rangeTH = 0 + diffT
#rangeTL = 0 - diffT
#rangeTH_F = 32 + (diffT * units.DegC).to('DegF')
#rangeTL_F = 32 - (diffT * units.DegC).to('DegF')


if level != 'surface':
    if (level == 975) or (level == 850) or (level == 700):
        steps = 30
    elif (level == 500):
        steps = 60
    elif (level == 300) or (level == 200):
        steps = 120
    
    # Set attributes for plotting contours
    if "pressure_heights" in factorsPart:
        pressure_heights = declarative.ContourPlot()
        pressure_heights.data = ds
        pressure_heights.field = 'Geopotential_height_isobaric'
        pressure_heights.level = level * units.hPa
        pressure_heights.time = plot_time
        pressure_heights.contours = list(range(0, 12000, steps))
        pressure_heights.clabels = True
        pressure_heights.smooth_contour = smoothing
        plots_list.append(pressure_heights)
    
    if "temp_contours" in factorsPart:
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
        temp_contours.smooth_contour = smoothing
        plots_list.append(temp_contours)
        
    if "temp_fill" in factorsPart:
        temp_fill = declarative.FilledContourPlot()
        temp_fill.data = ds
        temp_fill.field = 'Temperature_isobaric'
        temp_fill.level = level * units.hPa
        temp_fill.time = plot_time
        temp_fill.contours = list(range(-100, 100, 1)) # rangeTL, rangeTH
        temp_fill.colormap = 'coolwarm'
        temp_fill.colorbar = 'horizontal'
        temp_fill.plot_units = 'degC'
        plots_list.append(temp_fill)
        
    # Add wind barbs
    if "barbs" in factorsPart:
        barbs = declarative.BarbPlot()
        barbs.data = ds
        barbs.time = plot_time
        barbs.field = ['u-component_of_wind_isobaric', 'v-component_of_wind_isobaric']
        barbs.level = level * units.hPa
        barbs.skip = (barbfactor, barbfactor)
        barbs.plot_units = 'knot'
        plots_list.append(barbs)
        
    # Set the attributes for the map
    # and put the contours on the map
    panel.layers = ['states', 'coastline', 'borders']
    panel.title = f'Bailey, Sam - {area} {level}mb Contour Map {timestampAlp}, {dTime} Hour Forecast'
else:
    # Set attributes for plotting contours
    if "pressure" in factorsPart:
        pressure = declarative.ContourPlot()
        pressure.data = ds
        pressure.field = 'Pressure_reduced_to_MSL_msl'
        pressure.level = None
        pressure.time = plot_time
        pressure.contours = list(range(0, 2000, 4))
        pressure.clabels = True
        pressure.plot_units = 'hPa'
        pressure.smooth_contour = smoothing
        plots_list.append(pressure)
        
    # Set attributes for plotting filled contours
    if "temp_fill" in factorsPart:
        temp_fill = declarative.FilledContourPlot()
        temp_fill.data = ds
        temp_fill.field = 'Temperature_height_above_ground'
        temp_fill.level = 2 * units.m
        temp_fill.time = plot_time
        temp_fill.contours = list(range(-68, 132, 2)) # rangeTL_F, rangeTH_F
        temp_fill.colormap = 'coolwarm'
        temp_fill.colorbar = 'horizontal'
        temp_fill.plot_units = 'degF'
        plots_list.append(temp_fill)
        
    if "temp_contours" in factorsPart:
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
        temp_contours.smooth_contour = smoothing
        plots_list.append(temp_contours)
        
    # Set attributes for plotting wind barbs
    if "barbs" in factorsPart:
        barbs = declarative.BarbPlot()
        barbs.data = ds
        barbs.time = plot_time
        barbs.field = ['u-component_of_wind_height_above_ground',
                       'v-component_of_wind_height_above_ground']
        barbs.level = 10 * units.m
        barbs.skip = (barbfactor, barbfactor)
        barbs.plot_units = 'knot'
        plots_list.append(barbs)
        
    # Set the attributes for the map
    # and put the contours on the map
    #panel.plots = factorsPart
    panel.title = f'Bailey, Sam - {area} Surface Contour Map {timestampAlp}, {dTime} Hour Forecast'
panel.layers = ['states', 'coastline', 'borders']

# Determine which things are plotted

#if "barbs" in factorsPart:
#    panel.plots = [barbs]
#elif ("barbs" in factorsPart) and ("pressure" in factorsPart):
#    panel.plots = [barbs, pressure]

panel.plots = plots_list


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
        pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {dTime}H, {area} {level}mb Contour Map, {dpiSet} DPI - Bailey, Sam.png', dpi=dpiSet, bbox_inches='tight')
        save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {dTime}H, {area} {level}mb Contour Map, {dpiSet} DPI - Bailey, Sam.png')
        save.show()
    else:
        pc.save(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {dTime}H, {area} Surface Contour Map, {dpiSet} DPI - Bailey, Sam.png', dpi=dpiSet, bbox_inches='tight')
        save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {dTime}H, {area} Surface Contour Map, {dpiSet} DPI - Bailey, Sam.png')
        save.show()
    print("> Map successfully saved!")
else:
    if level != 'surface':
        pc.save(f'../Maps/{saveLocale}/{timestampNum}, {dTime}H, {area} {level}mb Contour Map, {dpiSet} DPI - Bailey, Sam.png', dpi=dpiSet, bbox_inches='tight')
        save = Image.open(f'../Maps/{saveLocale}/{timestampNum}, {dTime}H, {area} {level}mb Contour Map, {dpiSet} DPI - Bailey, Sam.png')
        save.show()
        os.remove(f'../Maps/{saveLocale}/{timestampNum}, {dTime}H, {area} {level}mb Contour Map, {dpiSet} DPI - Bailey, Sam.png')
    else:
        pc.save(f'../Maps/{saveLocale}/{timestampNum}, {dTime}H, {area} Surface Contour Map, {dpiSet} DPI - Bailey, Sam.png', dpi=dpiSet, bbox_inches='tight')
        save = Image.open(f'../Maps/{saveLocale}/{timestampNum}, {dTime}H, {area} Surface Contour Map, {dpiSet} DPI - Bailey, Sam.png')
        save.show()
        os.remove(f'../Maps/{saveLocale}/{timestampNum}, {dTime}H, {area} Surface Contour Map, {dpiSet} DPI - Bailey, Sam.png')