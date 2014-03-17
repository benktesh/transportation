###########################################
# Master Script for the Travel Time Cost Surface Model (TTCSM)
# The TTCSM models travel time based on user defined Cost Surfaces, Speed Surface
# and least cost path modeling techniques.  See the TTCSM Standard Operating Procedure document
# for details about running the TTCSM.
#
# Draft version Date: June 25th, 2010
# Script Written By:  Kirk Sherrill NPS-NRPC-I&M GIS Program
# 
#
# Suggested Citation: NPS-NRPC (2010). Travel Time Cost Surface Model, Version 2.0, Natural Resource Program Center – Inventory & Monitoring Program, Fort Collins, Colorado.
#
##########################################


# Import system modules
import sys, string, os, arcgisscripting, math

# Create the Geoprocessor object
gp = arcgisscripting.create()

# Check out any necessary ArcGIS licenses
gp.CheckOutExtension("spatial")

# Load required toolboxes...
gp.AddToolbox("C:/arcgis/ArcToolbox/Toolboxes/Spatial Analyst Tools.tbx")
gp.AddToolbox("C:/arcgis/ArcToolbox/Toolboxes/Conversion Tools.tbx")


###################################################
# Start of Parameters requiring set up.
###################################################

## Required Data Layers
startLocation= "D:\\CostSurface\\romo\\test_data\\BearLakeOnly.shp"                          ## Location(s) to calculate start point(s) for cost or path distance calculation
roadsData = "D:\\CostSurface\\romo\\test_data\\Roads.shp"                             ## Road Network
trailsData = "D:\\CostSurface\\romo\\test_data\\Trails.shp"                           ## Trail Network
DEM = "D:\\CostSurface\\romo\\test_data\\dem"                                         ## Digital Elevation Model location
destinations = "D:\\CostSurface\\romo\\test_data\\Destination_PointsTwo.shp"             ##Path to the destinations feature class data
costSurfaceTable = "D:\\CostSurface\\romo\\workspace2\\costSurfaceTable.txt"           ## costSurface Cost Surface Table location
workspace = "D:\\CostSurface\\romo\\workspace2\\"                                      ## Setting workspace variable
logFileName = workspace + "AA_TTCSM_logfile.txt"                                                ## Log File for the costSurfaceModelMS.py


## General Model Parameters
walkingSpeed = "3"                                                                            ## Average walking speed for the scenario when walking a smooth flat surface 
maxSlope = "40"                                                                                 ## Value in degrees defined as being to steep for travel
timeCap = "28800"                                                                               ## Maximum cost distance travel time calculated in seconds (28800/3600 = 8 hours).
trails = "yes"                                                                                  ## Variable defining if a trail network is being used.  If not available set to "no", so speed surface
                                                                                                ## calculation doesn't attempt to use the network.
                                     
##Travel Time Modeling Parameters 
usePathDistance = "yes"                                                                         ##Switch to use path distance or cost distance travel time calculation.  If it is desired to use normal cost distance travel time calculation then leave blank i.e. "" or if path distance is desired input "yes"
vertValueZero = "1"                                                                             ##Value of the vertical factor graph at a slope value of zero.  This usually will be 1, but can be changed as desired.
verticalGraphType = "Inverse_Linear"                                                        ##Select one of the following vertical factor graph (weights)to be used in path distance modeling. : "Binary","Linear", ## "Sym_linear", "Inverse_Linear", "Sym_Inverse_Linear", "Cos", "Sec", "Cos_Sec", "Sec_Cos", "Table".  See documentation for further definition.          
verticalGraph = ""                                                                              ##User specified vertical factor graph to be used in path distance modeling if verticalGraphType of "Table" is selected.
timeCalculation = "RoundTrip"                                                                     ##Switch defining if one way or round trip time calculations are desired. "RoundTrip" = Round trip, "Oneway" only travel out travel time is calculated.                                                                         
leastCostPath = "yes"                                                                           ##Switch defining if the used least cost paths are desired."Yes" = yes output least cost paths, "No" = no least cost path output.   If least cost cost is desired must supply a destinations feature class layer.                      

###################################################
# End of Parameters requiring set up.
###################################################

############################################ 
## Below are paths which are hard coded

# Setting the Geoprocessing workspace
gp.Workspace = workspace

usePDLC = usePathDistance.lower()
if usePDLC == "yes":
    suffix = verticalGraphType  #determining which suffix to use for output files flagging for either cost or path distance with the respective vfg type used.
else:
    suffix = "Cost_Distance"    #determining which suffix to use for output files flagging for either cost or path distance with the respective vfg type used. 

extentDEM = workspace + "extentDEM"
belowSlope = workspace + "belowSlope"
slope = workspace + "slope"
roadSpeed = workspace + "roadSpeed"
costSurface = workspace + "output\\costSurface.img"                  #Cost Surface Grid
speedSurface = workspace + "output\\speedSurface.img"                #has Road and Trail Speed as well as Speed everywhere else in Seconds per Meter with out impedence included.
travelCost = workspace + "output\\travelCost.img"                     #Final travel cost surface grid to be input into the cost/path distance models. It is costSuface * speedSurface
travelTimeOut = workspace + "travelTimeOut_" + suffix + ".img"         #calculated one way (travel out) travel time - output from the cost distance model (using either Cost Distance or Path Distance).
costPathsOut = workspace + "output\\costPathsOut_" + suffix + ".shp"            #merged Out travel cost paths shapefile        



##Loading TTCSM modules

import npsTTCSMModule

reload (npsTTCSMModule)

from npsTTCSMModule import *


scriptMsg = ""


##Beginning routine to run indivual TTCSM modules

try:
    # Open log file for writing
    logFile = open(logFileName, "a")
    
    a = demBasedMS (DEM, extentDEM, slope, maxSlope, belowSlope, workspace)        #Dem Module
    print "demBased return code = " + str(a)
    statusA = "demBasedMS " + " << " + str(a)
    logFile.write(statusA + "\n")
    if a == 0:
        scriptMsg = "ttcsm model bailed...\nProblems with demBasedMS.py "
        logFile.write(scriptMsg)
        raise Exception, scriptMsg
    
    b = costSurfaceMS (costSurfaceTable, belowSlope, DEM, workspace, costSurface)       #Cost Surface Module
    print "costSurfaceMS return code = " + str(b)
    statusB = "costSurfaceMS " + " << " + str(b)
    logFile.write(statusB + "\n")
    if b == 0:
        scriptMsg = "ttcsm model bailed...\nProblems with costSurfaceMS.py "
        logFile.write(scriptMsg)
        raise Exception, scriptMsg
    
    c = speedSurfaceMS (roadsData, DEM, workspace, extentDEM, slope, roadSpeed, trailsData, speedSurface, trails, walkingSpeed)   #Speed Surface Module               
    print "speedSurfaceMS return code = " + str(c)
    statusC = "speedSurfaceMS " + " << " + str(c)
    logFile.write(statusC + "\n")
    if c == 0:
        scriptMsg = "ttcsm model bailed...\nProblems with speedSurfaceMS.py "
        logFile.write(scriptMsg)
        raise Exception, scriptMsg
    
    d = travelCostSurfaceMS (speedSurface, costSurface, travelCost, DEM, suffix, workspace)  #Travel Cost Surface Module                
    print "travelCostSurfaceMS return code = " + str(d)
    statusD = "travelCostSurfaceMS " + " << " + str(d)
    logFile.write(statusD + "\n")
    if d == 0:
        scriptMsg = "ttcsm model bailed...\nProblems with travelCostSurfaceMS.py "
        logFile.write(scriptMsg)
        raise Exception, scriptMsg
    
    e = travelTimeOutMS (startLocation, travelCost, DEM, maxSlope, usePathDistance, verticalGraphType, vertValueZero, verticalGraph, timeCap, workspace, suffix, leastCostPath, destinations)  #Travel Time out (i.e. Oneway) module               
    print "travelTimeOutMS return code = " + str(e)
    statusE = "travelTimeOutMS " + " << " + str(e)
    logFile.write(statusE + "\n")
    if e == 0:
        scriptMsg = "ttcsm model bailed...\nProblems with travelTimeOutMS.py "
        logFile.write(scriptMsg)
        raise Exception, scriptMsg
    
    timeCalculationLC = timeCalculation.lower()
    if timeCalculationLC == "roundtrip":
        f = travelTimeBackMS (startLocation, travelCost, travelTimeOut, DEM, maxSlope,usePathDistance, verticalGraphType, vertValueZero, verticalGraph, timeCap, workspace, suffix, timeCalculation, leastCostPath, destinations, costPathsOut)  #Travel Time back (i.e. Round Trip) module                 
        print "travelTimeBackMS return code = " + str(f)
        statusF = "travelTimeBackMS " + " << " + str(f)
        logFile.write(statusF + "\n")
        if f == 0:
            scriptMsg = "ttcsm model bailed...\nProblems with travelTimeBackMS.py "
            logFile.write(scriptMsg)
            raise Exception, scriptMsg
    else:
        print "Out Back Travel Time Not Selected"
    
except:
    print scriptMsg
    print "ttcsm model Script Not Working\nSee log file " + logFileName + " for more details"

finally:
    logFile.close()
