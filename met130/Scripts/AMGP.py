################################################
#                                              #
#       Automated Map Generation Program       #
#                                              #
#            Author: Sam Bailey                #
#        Last Revised: Apr 13, 2022            #
#                Version 0.2.0                 #
#                                              #
#        AMGP Created on Mar 09, 2022          #
#                                              #
################################################

################################################
# New_Map.py, AMGP Version 0.2.0 Manual:       #
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
import glob
import contextlib

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

version = "0.2.0"

# Opening the config file and manual
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
    global loaded
    global title
    global noShow
    
    print("<menu> Input commands, or type 'help'.")
    comm = input("<input> ")
    
    command = comm.split(" ")
    
    if command[0] == "help":
        for line in list(range(1, 58, 1)):
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
            singleLoads()
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
        singleLoads()
        inputChain()
    elif command[0] == 'edit':
        if command[1] in ["Level", "Date", "Delta", "Factors", "Area", "DPI", "Scale", "PRF", "BF", "Smooth", "Projection"]:
            if command[1] == "Level":
                loaded.update({'level':command[2]})
            if command[1] == "Date":
                if command[2] == 'recent':
                    loaded.update({'date':command[2]})
                elif command[2] == "today":
                    loaded.update({'date':f'{command[2]}, {command[3]}'})
                else:
                    loaded.update({'date':f'{command[2]}, {command[3]}, {command[4]}, {command[5]}'})
            if command[1] == "Delta":
                loaded.update({'delta':command[2]})
            if command[1] == "Factors":
                blankFactors = []
                count = 0
                if command[2] == "add":
                    blankFactors = loaded['factors'].split(', ')
                    for item in command:
                        if count > 2:
                            blankFactors.append(command[count])
                        count += 1
                elif command[2] == "remove":
                    blankFactors = loaded['factors'].split(', ')
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
                loaded.update({'factors':fullFactors})
            if command[1] == "Area":
                loaded.update({'area':command[2]})
            if command[1] == "DPI":
                loaded.update({'dpi':command[2]})
            if command[1] == "Scale":
                loaded.update({'scale':command[2]})
            if command[1] == "PRF":
                loaded.update({'prfactor':command[2]})
            if command[1] == 'BF':
                loaded.update({'barbfactor':command[2]})
            if command[1] == "Smooth":
                loaded.update({'smoothing':command[2]})
            if command[1] == "Projection":
                loaded.update({'projection':command[2]})
            singleLoads()
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
        if os.path.isdir("../Temp"):
            ClearTemp()
        product = run(loaded, title)
        SaveMap(product, S, A, title, noShow)
        inputChain()
    elif command[0] == 'mode':
        global mode
        mode = 1
        multiMode()
    elif command[0] == 'quit':
        ClearTemp()
        sys.exit("<quit> The process was terminated.")
    else:
        print("<error> That is not a valid command!")
        inputChain()
        
#      ------ End inputChain() ------
        
    
def multiMode():
    global Set
    global loaded
    levels = []
    
    print("<menu> Input commands, or type 'help'.")
    comm = input("<input> ")
    
    command = comm.split(" ")
    
    if command[0] == "help":
        for line in list(range(1, 58, 1)):
            print(manual[line], end='')
        multiMode()
    
    if command[0] == "list":
        print("<list> Type 'time' to set and print the current time.")
        print("<list> Type 'preset {name}' to load a map preset.")
        print("<list> Type 'preset list' to list available presets.")
        print("<list> Type 'edit {parameter}' to edit a given parameter.")
        print("<list> Type 'run' to run with the current settings.")
        print("<list> Type 'quit' to exit without running.")
        multiMode()
    
    
    if command[0] == 'time':
        getTime()
        multiMode()
    elif command[0] == 'preset':
        if command[1] == 'list':
            keys = str(list(config['presets'].keys()))
            print("<presets> Below is the list of all currently loaded presets:")
            print("<presets> " + keys)
            print("<presets> To edit or add presets, please switch back to individual mode.")
            multiMode()
        else:
            presetLoad(command[1])
            multiLoads()
            multiMode()
    elif command[0] == 'edit':
        if command[1] in ['Date', 'DLoop', 'Jump' 'Delta', 'FCLoop', 'Levels']:
            if command[1] == 'Date':
                if command[2] == 'recent':
                    Set.update({'date':command[2]})
                elif command[2] == "today":
                    Set.update({'date':f'{command[2]}, {command[3]}'})
                else:
                    Set.update({'date':f'{command[2]}, {command[3]}, {command[4]}, {command[5]}'})
            elif command[1] == 'DLoop':
                Set.update({'dloop':command[2]})
            elif command[1] == 'Jump':
                Set.update({'jump':command[2]})
            elif command[1] == 'Delta':
                Set.update({'delta':command[2]})
            elif command[1] == 'FCLoop':
                Set.update({'fcloop':command[2]})
            elif command[1] == 'Levels':
                blankLevels = []
                count = 0
                if command[2] == "add":
                    blankLevels = Set['levels'].split(', ')
                    for item in command:
                        if count > 2:
                            blankLevels.append(command[count])
                        count += 1
                elif command[2] == "remove":
                    blankLevels = Set['levels'].split(', ')
                    for item in command:
                        if count > 2:
                            if command[count] in blankLevels:
                                blankLevels.pop(blankLevels.index(command[count]))
                            else:
                                print("<error> That is not a valid factor to remove!")
                                multiMode()
                        count += 1
                else:
                    for item in command:
                        if count > 1:
                            blankLevels.append(command[count])
                        count += 1
                Set.update({'levels':', '.join(blankLevels)})
        
        print(command[0], command[1], command[2], Set['delta'])
        multiLoads()
        multiMode()
        
            
            
    elif command[0] == 'paste':
        multiLoads()
        multiMode()
    elif command[0] == 'run':
        save('prev')
        panels = []
        gif = False
        
        gifq = input("<run> Would you like to save these files as a .gif? [y/n]: ")
        if gifq == 'y':
            gif = True
        assigned = input("<run> Is this product for an assignment? [y/n]: ")
        if assigned == 'y':
            doAssign = True
        else:
            doAssign = False
        if gif:
            gifname = input("<run> What would you like to call this .gif?: ")
        date = Set['date']
        dloop = int(Set['dloop'])
        jump = int(Set['jump'])
        delta = int(Set['delta'])
        fcloop = int(Set['fcloop'])
        fchours = [delta]
        dates = [0]
        levels = Set['levels'].split(', ')
        
        while fcloop >= 1:
            fchours.append(delta + (fcloop * 6))
            fcloop = fcloop - 1
            
        while dloop >= 1:
            dates.append(dloop * jump)
            dloop = dloop - 1
        
        while dloop <= -1:
            dates.append(dloop * jump)
            dloop = dloop + 1
        
        overrides = {}
        for fch in fchours:
            for dt in dates:
                for lvl in levels:
                    overrides.update({'fcHour':fch,'level':lvl,'date':FromDatetime((ParseTime(date).time + timedelta(hours=dt))).ToString()})
                    product = run(loaded, '', **overrides)
                    if gif:
                        panels.append(product)
                        print("<run> Map panel created successfully")
                    else:
                        SaveMap(product, True, doAssign, '', True)
                        
        if gif:
            c = 0
            for panel in panels:
                SaveMap(panel, False, False, f'{c:03d}', True)
                #if c == 0:
                #    SaveMap(panel, False, False, f'{c:03d}c', True)
                c = c + 1
            frames = []
            for image in reversed(glob.glob("../Maps/Temp/*.png")):
                frames.append(Image.open(image)) 
            frame_one = frames[0]
            if doAssign:
                frame_one.save(f"../Maps/Assignment_Maps/{gifname}.gif", format="GIF", append_images=frames, save_all=True, duration=1500, loop=0)
            else:
                frame_one.save(f"../Maps/Test_Maps/{gifname}.gif", format="GIF", append_images=frames, save_all=True, duration=1500, loop=0)
            print("<run> Gif created successfully")
            ClearTemp()
            
        multiMode()
        
    elif command[0] == 'mode':
        global mode
        mode = 0
        inputChain()
    elif command[0] == 'quit':
        ClearTemp()
        sys.exit("<quit> The process was terminated.")
    else:
        print("<error> That is not a valid command!")
        multiMode()

        
# Save a preset to the config file
def save(name):
    saveState = {"level":f"{loaded['level']}","date":f"{loaded['date']}","delta":f"{loaded['delta']}","factors":f"{loaded['factors']}","area":f"{loaded['area']}","dpi":f"{loaded['dpi']}","scale":f"{loaded['scale']}","prfactor":f"{loaded['prfactor']}","barbfactor":f"{loaded['barbfactor']}","smoothing":f"{loaded['smoothing']}","projection":f"{loaded['projection']}"}
    config['presets'][f'{name}'] = saveState
    with open("config.json", "w") as J:
        json.dump(config, J)

# Load a preset from the config file
def presetLoad(loadedPreset):
    global loaded
    loaded = config['presets'][f'{loadedPreset}']
    
def setInit():
    global Set
    Set = {'date':'recent','delta':0,'jump':3,'levels':'surface','dloop':0,'fcloop':0}
    
# Dump the loaded preset's contents
def singleLoads():
    print(f"<loaded> Level: {loaded['level']}")
    print(f"<loaded> Date: {loaded['date']}")
    print(f"<loaded> Delta: {loaded['delta']}")
    print(f"<loaded> Factors: {loaded['factors']}")
    print(f"<loaded> Area: {loaded['area']}")
    print(f"<loaded> DPI: {loaded['dpi']}")
    print(f"<loaded> Scale: {loaded['scale']}")
    print(f"<loaded> PRF (Point Reduction Scale): {loaded['prfactor']}")
    print(f"<loaded> BF (Barb Factor): {loaded['barbfactor']}")
    print(f"<loaded> Smooth: {loaded['smoothing']}")
    print(f"<loaded> Projection: {loaded['projection']}")
    
def multiLoads():
    print(f"<settings> Below are the settings from the loaded preset:")
    singleLoads()
    print(f"<settings> Below are the settings from the current multiRun settings:")
    print(f"<settings> Date: {Set['date']}")
    print(f"<settings> DLoop: {Set['dloop']}")
    print(f"<settings> Delta: {Set['delta']}")
    print(f"<settings> Jump: {Set['jump']}")
    print(f"<settings> Levels: {Set['levels']}")
    print(f"<settings> FCLoop: {Set['fcloop']}")
    
    
class Time(object):
    def __init__(self, Date):
        rec = False
        splitDate = Date.split(", ")
        if splitDate[0] == 'recent':
            rec = True
        elif splitDate[0] == 'today':
            givenTime = datetime(currentTime.year, currentTime.month, currentTime.day, int(splitDate[1]))
        else:
            givenTime = datetime(int(splitDate[0]), int(splitDate[1]), int(splitDate[2]), int(splitDate[3]))
            
        if (givenTime < datetime(1931, 1, 2)):
            sys.exit("<error> The date you entered is out of range!")
        elif (givenTime < datetime(1979, 1, 1)):
            print("<warning> The date you entered is out of range for gridded data.")
        
        
        if rec:
            currentTimeGridded = currentTime
            if currentTime.hour >= 21:
                rHour = 21
                urHour = 12
                grHour = 18
            elif currentTime.hour >= 18:
                rHour = 18
                urHour = 12
                grHour = 12
            elif currentTime.hour >= 15:
                rHour = 15
                urHour = 12
                grHour = 12
            elif currentTime.hour >= 12:
                rHour = 12
                urHour = 12
                grHour = 6
            elif currentTime.hour >= 9:
                rHour = 9
                urHour = 0
                grHour = 6
            elif currentTime.hour >= 6:
                rHour = 6
                urHour = 0
                grHour = 0
            elif currentTime.hour >= 3:
                rHour = 3
                urHour = 0
                grHour = 0
            else:
                rHour = 0
                urHour = 0
                grHour = 18
                currentTimeGridded = currentTimeGridded - timedelta(days=1)
            rDay = currentTime.day
            grDay = currentTimeGridded.day
            rMonth = currentTime.month
            grMonth = currentTimeGridded.month
            rYear = currentTime.year
            grYear = currentTimeGridded.year

            self.time = datetime(rYear, rMonth, rDay, rHour)
            self.timeUA = datetime(rYear, rMonth, rDay, urHour)
            self.timeG = datetime(grYear, grMonth, grDay, grHour)
        else:
            if givenTime.hour >= 21:
                Hour = 21
                uHour = 12
                gHour = 18
            elif givenTime.hour >= 18:
                Hour = 18
                uHour = 12
                gHour = 18
            elif givenTime.hour >= 15:
                Hour = 15
                uHour = 12
                gHour = 12
            elif givenTime.hour >= 12:
                Hour = 12
                uHour = 12
                gHour = 12
            elif givenTime.hour >= 9:
                Hour = 9
                uHour = 0
                gHour = 6
            elif givenTime.hour >= 6:
                Hour = 6
                uHour = 0
                gHour = 6
            elif givenTime.hour >= 3:
                Hour = 3
                uHour = 0
                gHour = 0
            else:
                Hour = 0
                uHour = 0
                gHour = 0

            self.time = datetime(givenTime.year, givenTime.month, givenTime.day, Hour)
            self.timeUA = datetime(givenTime.year, givenTime.month, givenTime.day, uHour)
            self.timeG = datetime(givenTime.year, givenTime.month, givenTime.day, gHour)
        
        
        self.ds = f"{givenTime.year}-{self.time.strftime('%m')}-{self.time.strftime('%d')}"
        self.tsnum = f"{givenTime.year}-{self.time.strftime('%m')}-{self.time.strftime('%d')}-{self.time.strftime('%H')}Z"
        self.tsalp = f"{self.time.strftime('%b')} {givenTime.day}, {givenTime.year} - {Hour}Z"
        self.tsnumUA = f"{givenTime.year}-{self.timeUA.strftime('%m')}-{self.timeUA.strftime('%d')}-{self.timeUA.strftime('%H')}Z"
        self.tsalpUA = f"{self.timeUA.strftime('%b')} {givenTime.day}, {givenTime.year} - {uHour}Z"
        self.dsG = f"{givenTime.year}-{self.timeG.strftime('%m')}-{self.timeG.strftime('%d')}"
        self.tsnumG = f"{givenTime.year}-{self.timeG.strftime('%m')}-{self.timeG.strftime('%d')}-{self.timeG.strftime('%H')}Z"
        self.tsalpG = f"{self.timeG.strftime('%b')} {givenTime.day}, {givenTime.year} - {gHour}Z"
        
    def ToString(self):
        return f"{self.time.year}, {self.time.month}, {self.time.day}, {self.time.hour}"
    

def ParseTime(string):
    return Time(string)

def FromDatetime(datetimeObj):
        customTimeFormat = f"{datetimeObj.year}, {datetimeObj.month}, {datetimeObj.day}, {datetimeObj.hour}"
        newTime = ParseTime(customTimeFormat)
        return newTime
    
class Datum(object):
    def __init__(self, TimeObj, delta, rewind):
        
        time = TimeObj.time
        griddedTime = TimeObj.timeG
        upperAirTime = TimeObj.timeUA
        
        adjustedTime = time - timedelta(hours=rewind)
        adjustedGriddedTime = griddedTime - timedelta(hours=rewind)
        adjustedUpperAirTime = upperAirTime - timedelta(hours=rewind)
        
        self.plot_time = adjustedGriddedTime + timedelta(hours=delta)
    
        recentness = currentTime - adjustedTime
        if adjustedTime.year < 2019:
            self.sfcDat = pd.read_csv(f'http://bergeron.valpo.edu/archive_surface_data/{adjustedTime:%Y}/{adjustedTime:%Y%m%d}_metar.csv', parse_dates=['date_time'], na_values=[-9999], low_memory=False)
            self.weather_format = 'present_weather'
            self.sfcDat['tmpf'] = (self.sfcDat.air_temperature.values * units.degC).to('degF')
            self.sfcDat['dwpf'] = (self.sfcDat.dew_point_temperature.values * units.degC).to('degF')
        elif recentness < timedelta(days=14):
            data = StringIO(urlopen('http://bergeron.valpo.edu/current_surface_data/'f'{adjustedTime:%Y%m%d%H}_sao.wmo').read().decode('utf-8', 'backslashreplace'))
            self.sfcDat = metar.parse_metar_file(data, year=adjustedTime.year, month=adjustedTime.month)
            self.sfcDat['tmpf'] = (self.sfcDat.air_temperature.values * units.degC).to('degF')
            self.sfcDat['dwpf'] = (self.sfcDat.dew_point_temperature.values * units.degC).to('degF')
            self.weather_format = 'current_wx1_symbol'
        else:
            print("<warning> The date you have selected has no surface data available!")
            self.sfcDat = None
        self.uaDat = IAStateUpperAir.request_all_data(adjustedUpperAirTime)
        self.uaDat = add_station_lat_lon(self.uaDat, 'station').dropna(subset=['latitude', 'longitude'])
        self.uaDat = self.uaDat[self.uaDat.station != 'KVER'] # "central Missouri" station that shouldn't be there, due to faulty lat-lon data
        self.uaDat['dewpoint_depression'] = self.uaDat['temperature'] - self.uaDat['dewpoint']
        
        if (recentness < timedelta(days=14)):
            self.grd = xr.open_dataset('https://thredds.ucar.edu/thredds/dodsC/grib'f'/NCEP/GFS/Global_onedeg/GFS_Global_onedeg_{adjustedGriddedTime:%Y%m%d}_{adjustedGriddedTime:%H%M}.grib2').metpy.parse_cf()
        elif (adjustedGriddedTime >= datetime(2004, 3, 2)):
            try:
                self.grd = xr.open_dataset('https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-g3-anl-files-old/'f'{adjustedGriddedTime:%Y%m/%Y%m%d}/gfsanl_3_{adjustedGriddedTime:%Y%m%d_%H}00_000.grb').metpy.parse_cf()
            except:
                self.grd = xr.open_dataset('https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-003-files-old/'f'{adjustedGriddedTime:%Y%m/%Y%m%d}/gfs_3_{adjustedGriddedTime:%Y%m%d_%H}00_{delta:03d}.grb2').metpy.parse_cf()
        elif (adjustedGriddedTime >= datetime(1979, 1, 1)):
            self.grd = xr.open_dataset('https://www.ncei.noaa.gov/thredds/dodsC/model-narr-a-files/'f'{adjustedGriddedTime:%Y%m/%Y%m%d}/narr-a_221_{adjustedGriddedTime:%Y%m%d_%H}00_000.grb').metpy.parse_cf()
        else:
            print("<warning> The date you have selected has no gridded data available!")
            
            
def PullData(time, delta, rewnd):
    return Datum(time, delta, rewnd)

def GriddedCalculations(Data, level):
    
    plot_time = Data.plot_time
    
    if level == 'surface':
        tmpk = Data.grd.Temperature_height_above_ground.metpy.sel(vertical=2*units.m, time=plot_time)
        uwind = Data.grd['u-component_of_wind_height_above_ground'].metpy.sel(vertical=10*units.m, time=plot_time)
        vwind = Data.grd['v-component_of_wind_height_above_ground'].metpy.sel(vertical=10*units.m, time=plot_time)
        Data.grd['wind_speed_height_above_ground'] = mpcalc.wind_speed(uwind, vwind)
    else:
        tmpk = Data.grd.Temperature_isobaric.metpy.sel(vertical=level*units.hPa, time=plot_time)
        uwind = Data.grd['u-component_of_wind_isobaric'].metpy.sel(vertical=level*units.hPa, time=plot_time)
        vwind = Data.grd['v-component_of_wind_isobaric'].metpy.sel(vertical=level*units.hPa, time=plot_time)
        Data.grd['wind_speed_isobaric'] = mpcalc.wind_speed(uwind, vwind)
    Data.grd['relative_vorticity'] = mpcalc.vorticity(uwind, vwind)
    Data.grd['temperature_advection'] = mpcalc.advection(tmpk, uwind, vwind)
    
    return Data

def ClearTemp():
    for subPath in os.listdir(f"../Maps/Temp"):
        if os.path.isdir(f"../Maps/Temp/{subPath}"):
            ClearTemp(f"../Maps/Temp/{subPath}")
            os.rmdir(f"../Maps/Temp/{subPath}")
        else:
            with contextlib.suppress(FileNotFoundError):
                os.remove(f"../Maps/Temp/{subPath}")
    
# The meat of the program
def run(values, titleOverride, **Override):
    
    rewind = 0
    # Handle quickrun overrides
    for k in Override:
        if k == "date":
            values.update({'date':Override[k]})
        if k == "fcHour":
            values.update({'delta':Override[k]})
        if k == "level":
            values.update({'level':Override[k]})
        if k == 'factors':
            values.update({'factors':Override[k]})
        if k == "adtnlRwnd":
            rewind = Override[k]
    
    values.update({'delta':int(values['delta'])})
    
    # Level
    if values['level'] != 'surface':
        level = int(values['level'])
    else:
        level = values['level']
        
    # Date
    Time = ParseTime(values['date'])
        
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
    Data = GriddedCalculations(PullData(Time, values['delta'], rewind), level)
    
    # Panel Preparation
    panel = declarative.MapPanel()
    panel.layout = (1, 1, 1)
    
    # Parse custom zoom feature
    simArea = values['area'].replace("+", "")
    simArea = simArea.replace("-", "")
    if simArea in area_dictionary:
        splitArea = Counter(values['area'])
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
        panel.area = f'{values["area"]}'

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
    if (Time.time >= datetime(2004, 3, 2)):
        Data.grd = Data.grd.sel(lat=latSlice, lon=lonSlice)
    
    panel.layers = ['states', 'coastline', 'borders']
    
    # Parsing the panel.area into a list, and doing math on it.
    areaList = list(panel.area)
    areaMap = map(int, areaList)
    mapList = list(areaMap)
    diffLat = int(mapList[1])-int(mapList[0])
    diffLon = int(mapList[3])-int(mapList[2])
    avgDiff = ((diffLat + diffLon)//2)
    scaledDiff = math.floor(avgDiff*float(values['scale']))

    # Determining projection
    midLon = (mapList[1]+mapList[0])//2
    midLat = (mapList[3]+mapList[2])//2
    if values['projection'] == '' or values['projection'] == 'custom':
        projection = ccrs.LambertConformal(central_longitude = midLon, central_latitude = midLat)
    else:
        projection = values['projection']
    panel.projection = projection
    
    
    # Factor Parsing
    plotslist = []
    factors = values['factors'].split(", ")
        # Gridded
    if level != 'surface':
        if "temp_fill" in factors:
            temp_fill = declarative.FilledContourPlot()
            temp_fill.data = Data.grd
            temp_fill.field = 'Temperature_isobaric'
            temp_fill.level = level * units.hPa
            temp_fill.time = Data.plot_time
            temp_fill.contours = list(range(-100, 101, 1)) # rangeTL, rangeTH
            temp_fill.colormap = 'coolwarm'
            temp_fill.colorbar = 'horizontal'
            temp_fill.plot_units = 'degC'
            plotslist.append(temp_fill)
            
        if "wind_speed_fill" in factors:
            wind_speed_fill = declarative.FilledContourPlot()
            wind_speed_fill.data = Data.grd
            wind_speed_fill.field = 'wind_speed_isobaric'
            wind_speed_fill.level = None
            wind_speed_fill.time = None
            wind_speed_fill.contours = list(range(10, 241, 20))
            wind_speed_fill.colormap = 'BuPu'
            wind_speed_fill.colorbar = 'horizontal'
            wind_speed_fill.plot_units = 'knot'
            plotslist.append(wind_speed_fill)
            
        if "temp_advect_fill" in factors:
            temp_advect_fill = declarative.FilledContourPlot()
            temp_advect_fill.data = Data.grd
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
            relative_vorticity_fill.data = Data.grd
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
            absolute_vorticity_fill.data = Data.grd
            absolute_vorticity_fill.field = 'Absolute_vorticity_isobaric'
            absolute_vorticity_fill.level = level * units.hPa
            absolute_vorticity_fill.time = Data.plot_time
            absolute_vorticity_fill.contours = list(range(-80, 81, 2))
            absolute_vorticity_fill.colormap = 'PuOr_r'
            absolute_vorticity_fill.colorbar = 'horizontal'
            absolute_vorticity_fill.scale = 1e5
            plotslist.append(absolute_vorticity_fill)
            
        if "height_contours" in factors:
            pressure_heights = declarative.ContourPlot()
            pressure_heights.data = Data.grd
            pressure_heights.field = 'Geopotential_height_isobaric'
            pressure_heights.level = level * units.hPa
            pressure_heights.time = Data.plot_time
            pressure_heights.contours = list(range(0, 12000, steps))
            pressure_heights.clabels = True
            pressure_heights.smooth_contour = int(values['smoothing'])
            plotslist.append(pressure_heights)
    
        if "temp_contours" in factors:
            temp_contours = declarative.ContourPlot()
            temp_contours.data = Data.grd
            temp_contours.field = 'Temperature_isobaric'
            temp_contours.level = level * units.hPa
            temp_contours.time = Data.plot_time
            temp_contours.contours = list(range(-100, 101, 5))
            temp_contours.linecolor = 'red'
            temp_contours.linestyle = 'dashed'
            temp_contours.clabels = True
            temp_contours.plot_units = 'degC'
            temp_contours.smooth_contour = int(values['smoothing'])
            plotslist.append(temp_contours)

        if "dew_contours" in factors:
            hPaLevel = level * units.hPa
            tmpIsoSel = Data.grd['Temperature_isobaric'].metpy.sel(vertical=hPaLevel)
            rhIsoSel = Data.grd['Relative_humidity_isobaric'].metpy.sel(vertical=hPaLevel)
            Data.grd['Dewpoint_isobaric'] = mpcalc.dewpoint_from_relative_humidity(tmpIsoSel, rhIsoSel)
            dew_contours = declarative.ContourPlot()
            dew_contours.data = Data.grd
            dew_contours.field = 'Dewpoint_isobaric'
            dew_contours.level = None
            dew_contours.time = Data.plot_time
            dew_contours.contours = list(range(-100, 101, 5))
            dew_contours.linecolor = 'green'
            dew_contours.linestyle = 'dashed'
            dew_contours.clabels = True
            #dew_contours.plot_units = 'degC'
            dew_contours.smooth_contours = int(values['smoothing'])
            plotslist.append(dew_contours)
        
        if "gridded_barbs" in factors:
            barbs = declarative.BarbPlot()
            barbs.data = Data.grd
            barbs.time = Data.plot_time
            barbs.field = ['u-component_of_wind_isobaric', 'v-component_of_wind_isobaric']
            barbs.level = level * units.hPa
            barbs.skip = (int(values['barbfactor']), int(values['barbfactor']))
            barbs.plot_units = 'knot'
            plotslist.append(barbs)
            
    else:
        if "temp_fill" in factors:
            temp_fill = declarative.FilledContourPlot()
            temp_fill.data = Data.grd
            temp_fill.field = 'Temperature_height_above_ground'
            temp_fill.level = 2 * units.m
            temp_fill.time = Data.plot_time
            temp_fill.contours = list(range(-68, 133, 2)) # rangeTL_F, rangeTH_F
            temp_fill.colormap = 'coolwarm'
            temp_fill.colorbar = 'horizontal'
            temp_fill.plot_units = 'degF'
            plotslist.append(temp_fill)
            
        if "wind_speed_fill" in factors:
            wind_speed_fill = declarative.FilledContourPlot()
            wind_speed_fill.data = Data.grd
            wind_speed_fill.field = 'wind_speed_height_above_ground'
            wind_speed_fill.level = None
            wind_speed_fill.time = None
            wind_speed_fill.contours = list(range(10, 201, 20))
            wind_speed_fill.colormap = 'BuPu'
            wind_speed_fill.colorbar = 'horizontal'
            wind_speed_fill.plot_units = 'knot'
            plotslist.append(wind_speed_fill)
            
        if "temp_advect_fill" in factors:
            temp_advect_fill = declarative.FilledContourPlot()
            temp_advect_fill.data = Data.grd
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
            relative_vorticity_fill.data = Data.grd
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
            pressure.data = Data.grd
            pressure.field = 'Pressure_reduced_to_MSL_msl'
            pressure.level = None
            pressure.time = Data.plot_time
            pressure.contours = list(range(0, 2000, 4))
            pressure.clabels = True
            pressure.plot_units = 'hPa'
            pressure.smooth_contour = int(values['smoothing'])
            plotslist.append(pressure)
            
        if "temp_contours" in factors:
            temp_contours = declarative.ContourPlot()
            temp_contours.data = Data.grd
            temp_contours.field = 'Temperature_height_above_ground'
            temp_contours.level = 2 * units.m
            temp_contours.time = Data.plot_time
            temp_contours.contours = list(range(-100, 101, 10))
            temp_contours.linecolor = 'red'
            temp_contours.linestyle = 'dashed'
            temp_contours.clabels = True
            temp_contours.plot_units = 'degF'
            temp_contours.smooth_contour = int(values['smoothing'])
            plotslist.append(temp_contours)
            
        if "dew_contours" in factors:
            dew_contours = declarative.ContourPlot()
            dew_contours.data = Data.grd
            dew_contours.field = 'Dewpoint_temperature_height_above_ground'
            dew_contours.level = 2 * units.m
            dew_contours.time = Data.plot_time
            dew_contours.contours = list(range(-100, 101, 10))
            dew_contours.linecolor = 'green'
            dew_contours.linestyle = 'dashed'
            dew_contours.clabels = True
            dew_contours.plot_units = 'degF'
            dew_contours.smooth_contour = int(values['smoothing'])
            plotslist.append(dew_contours)
            
        if "gridded_barbs" in factors:
            barbs = declarative.BarbPlot()
            barbs.data = Data.grd
            barbs.time = Data.plot_time
            barbs.field = ['u-component_of_wind_height_above_ground', 'v-component_of_wind_height_above_ground']
            barbs.level = 10 * units.m
            barbs.skip = (int(values['barbfactor']), int(values['barbfactor']))
            barbs.plot_units = 'knot'
            plotslist.append(barbs)
            
                    # Observations
    obsfields = []
    obscolors = []
    obslocations = []
    obsformats = []
    
    obs = declarative.PlotObs()
    if Data.sfcDat != None:
        if level == 'surface':
            obs.data = Data.sfcDat
        else:
            obs.data = Data.uaDat
        obs.time = Time.time
    
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
        obsfields.append(f'{Data.weather_format}')
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
        
    
    obs.fields = obsfields
    obs.colors = obscolors
    obs.formats = obsformats
    obs.locations = obslocations
    obs.reduce_points = float(values['prfactor'])
    
    if level == 'surface':
        obs.level = None
        obs.time_window = timedelta(minutes=15)
    else:
        obs.level = level * units.hPa
                            
            
    if ("temperature" in factors) or ("dewpoint" in factors) or ("dewpoint_depression" in factors) or ("height" in factors) or ("pressure" in factors) or ('current_weather' in factors) or ("barbs" in factors) or ("cloud_coverage" in factors):
        plotslist.append(obs)
        
    if obs in plotslist:
        observations = True
        if len(plotslist) > 1:
            griddeds = True
        else:
            griddeds = False
    else:
        observations = False
    if obs not in plotslist:
        griddeds = True
        
    if griddeds and (level == 'surface'):
        maptype = 2 # Surface Gridded Map
    elif griddeds and (level != 'surface'):
        maptype = 3 # Upper-air Gridded Map
    elif observations and (level == 'surface'):
        maptype = 0 # Surface Observation Map
    elif observations and (level != 'surface'):
        mapytpe = 1 # Upper-air Observation Map
    
        
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
    
    if maptype == 2:
        panel.title = f"Bailey, Sam - {values['area']} {sConTitle} {Time.tsalpG}, {values['delta']} Hour Forecast"
    elif maptype == 3:
        panel.title = f"Bailey, Sam - {values['area']} {level}mb {conTitle} {Time.tsalpG}, {values['delta']} Hour Forecast"
    elif maptype == 0:
        panel.title = f"Bailey, Sam - {values['area']} {sObsTitle} {Time.tsalp}"
    elif maptype == 1:
        panel.title = f"Bailey, Sam - {values['area']} {level}mb {obsTitle} {Time.tsalpUA}"
                            
    return {'panelSize':(scaledDiff, scaledDiff),'panel':panel,'timeObj':Time,'type':maptype,'values':values}
    
    
def SaveMap(product, doSave, assigned, titleOverride, noShow):
    
    conTitle = "Contour Map"
    sConTitle = "Surface Contour Map"
    obsTitle = "Map"
    sObsTitle = "Surface Map"
    
    if titleOverride != '':
        conTitle = titleOverride
        sConTitle = titleOverride
        obsTitle = titleOverride
        sObsTitle = titleOverride
    else:
        titleOverride = 'temp'
    
    if product['type'] == 0:
        daystamp = product['timeObj'].ds
        timestampNum = product['timeObj'].tsnum
        timestampAlp = product['timeObj'].tsalp
    elif product['type'] == 1:
        daystamp = product['timeObj'].ds
        timestampNum = product['timeObj'].tsnumUA
        timestampAlp = product['timeObj'].tsalpUA
    else:
        daystamp = product['timeObj'].dsG
        timestampNum = product['timeObj'].tsnumG
        timestampAlp = product['timeObj'].tsalpG
    
    pc = declarative.PanelContainer()
    pc.size = product['panelSize']
    pc.panels = [product['panel']]
    
    # Saving the map
    if assigned:
        saveLocale = 'Assignment_Maps'
    else:
        saveLocale = 'Test_Maps'

    OldDir = os.path.isdir(f'../Maps/{saveLocale}/{daystamp}')

    if doSave:
        if OldDir == False:
            os.mkdir(f'../Maps/{saveLocale}/{daystamp}')
        if product['type'] == 3:
            pc.save(f"../Maps/{saveLocale}/{daystamp}/{timestampNum}, {product['values']['delta']:02d}H, {product['values']['area']} {level}mb {conTitle}, {product['values']['dpi']} DPI - Bailey, Sam.png", dpi=int(product['values']['dpi']), bbox_inches='tight')
            save = Image.open(f"../Maps/{saveLocale}/{daystamp}/{timestampNum}, {product['values']['delta']:02d}H, {product['values']['area']} {level}mb {conTitle}, {product['values']['dpi']} DPI - Bailey, Sam.png")
            if noShow == False:
                save.show()
        elif product['type'] == 2:
            pc.save(f"../Maps/{saveLocale}/{daystamp}/{timestampNum}, {product['values']['delta']:02d}H, {product['values']['area']} {sConTitle}, {product['values']['dpi']} DPI - Bailey, Sam.png", dpi=int(product['values']['dpi']), bbox_inches='tight')
            save = Image.open(f"../Maps/{saveLocale}/{daystamp}/{timestampNum}, {product['values']['delta']:02d}H, {product['values']['area']} {sConTitle}, {product['values']['dpi']} DPI - Bailey, Sam.png")
            if noShow == False:
                save.show()
        elif product['type'] == 1:
            pc.save(f"../Maps/{saveLocale}/{daystamp}/{timestampNum}, {product['values']['area']} {level}mb {obsTitle}, {product['values']['dpi']} DPI - Bailey, Sam.png", dpi=int(product['values']['dpi']), bbox_inches='tight')
            save = Image.open(f"../Maps/{saveLocale}/{daystamp}/{timestampNum}, {product['values']['area']} {level}mb {obsTitle}, {product['values']['dpi']} DPI - Bailey, Sam.png")
            if noShow == False:
                save.show()
        elif product['type'] == 0:
            pc.save(f"../Maps/{saveLocale}/{daystamp}/{timestampNum}, {product['values']['area']} {sObsTitle}, {product['values']['dpi']} DPI - Bailey, Sam.png", dpi=int(product['values']['dpi']), bbox_inches='tight')
            save = Image.open(f"../Maps/{saveLocale}/{daystamp}/{timestampNum}, {product['values']['dpi']} {sObsTitle}, {product['values']['dpi']} DPI - Bailey, Sam.png")
            if noShow == False:
                save.show()
        print("<run> Map successfully saved!")
    else:
        if os.path.isdir("../Maps/Temp") == False:
            os.mkdir("../Maps/Temp")
        pc.save(f"../Maps/Temp/{titleOverride}.png", dpi=int(product['values']['dpi']), bbox_inches='tight')
        save = Image.open(f'../Maps/Temp/{titleOverride}.png')
        if noShow == False:
            save.show()


# --- End Definitions ---



# Init
area_dictionary = dict(config['areas'])
area_dictionary = {k: tuple(map(float, v.split(", "))) for k, v in area_dictionary.items()}

global quickRun
global noShow
quickRun = False
noShow = False

# Check for quickrun commands

if len(sys.argv) > 1:
    sys.exit()
    '''
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
                    run(loaded, '', **overrides)
                    
    elif sys.argv[1] == "-help":
        for line in list(range(60, 136, 1)):
            if line != 135:
                print(manual[line], end='')
            else:
                print(manual[line])
        '''
    #sys.exit()
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
    setInit()
    singleLoads()

    inputChain()