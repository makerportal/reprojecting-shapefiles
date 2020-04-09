################################################
# Reprojecting shapefiles to WGS84 (EPSG 4326)
# Written and tested in Python 3.6+
################################################
#
#
from osgeo import ogr, osr
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import numpy as np

driver = ogr.GetDriverByName('ESRI Shapefile') # start shapefile driver

# get the input layer
shapefile_folder = './ZIP_CODE_040114/' # location of shapefile to be reprojected
shapefile = ((os.listdir(shapefile_folder)[0]).split('.')[0]).split('_correct_CRS')[0] #name of shapefile
inDataSet = driver.Open(shapefile_folder+shapefile+'.shp') # open shapefile
inLayer = inDataSet.GetLayer() # get the first layer
inSpatialRef = inLayer.GetSpatialRef() # spatial reference of dataset (map coordinates, etc.)
inSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER) # using legacy axis

# output SpatialReference
outSpatialRef = osr.SpatialReference()
outSpatialRef.ImportFromEPSG(4326) # the output spatial reference (WGS84 = EPSG 4326)
outSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER) # using legacy axis

# create the CoordinateTransformation
coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef) # establish transform

shp_bbox = inLayer.GetExtent() # bounding box of shapefile
ll_x,ll_y,_ = coordTrans.TransformPoint(shp[0],shp[2]) # reprojected lower-left bounds for city
ur_x,ur_y,_ = coordTrans.TransformPoint(shp[1],shp[3]) # reprojected upper-right bounds for city
zoom = 0.1 # for zooming into and out of the shapefile (only important for visualization purposes)
bbox = [ll_x-zoom,ll_y-zoom,ur_x+zoom,ur_y+zoom] # bounding box for visualizing

# create the output layer
outputShapefile = shapefile_folder+shapefile+'_correct_CRS.shp' # new shapefile, reprojected (correct CRS)
if os.path.exists(outputShapefile):
    driver.DeleteDataSource(outputShapefile)
outDataSet = driver.CreateDataSource(outputShapefile)
outLayer = outDataSet.CreateLayer("layer1", geom_type=ogr.wkbPolygon) # ensure 2d polygons

outSpatialRef.MorphToESRI()
file = open(outputShapefile.split('.shp')[0]+'.prj', 'w') # this is a necessary file for some mapping tools
file.write(outSpatialRef.ExportToWkt())
file.close()

# add fields
inLayerDefn = inLayer.GetLayerDefn()
for i in range(0, inLayerDefn.GetFieldCount()):
    fieldDefn = inLayerDefn.GetFieldDefn(i)
    outLayer.CreateField(fieldDefn)

# get the output layer's feature definition
outLayerDefn = outLayer.GetLayerDefn()

# loop through the input features
inFeature = inLayer.GetNextFeature()
while inFeature:
    # get the input geometry
    geom = inFeature.GetGeometryRef() 
    # reproject the geometry
    geom.Transform(coordTrans)
    # create a new feature
    outFeature = ogr.Feature(outLayerDefn)
    # set the geometry and attribute
    outFeature.SetGeometry(geom)
    for i in range(0, outLayerDefn.GetFieldCount()):
        outFeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))
    # add the feature to the shapefile
    outLayer.CreateFeature(outFeature)
    # dereference the features and get the next input feature
    outFeature = None
    inFeature = inLayer.GetNextFeature()

# Save and close the shapefiles
inDataSet = None
outDataSet = None

#
#################################
# plotting city shapefile
#################################
#
fig,ax = plt.subplots(figsize=(12,9))
# Basemap, cylindrical projection for visualizing, at high resolution
m = Basemap(llcrnrlon=bbox[0],llcrnrlat=bbox[1],urcrnrlon=bbox[2],
           urcrnrlat=bbox[3],resolution='h', projection='cyl') 
shpe = m.readshapefile(shapefile_folder+shapefile+'_correct_CRS','layer1')
m.drawmapboundary(fill_color='#bdd5d5')
m.fillcontinents(color=plt.cm.tab20c(19))
parallels = np.linspace(bbox[1],bbox[3],5) # latitudes
m.drawparallels(parallels,labels=[True,False,False,False],fontsize=12)
meridians = np.linspace(bbox[0],bbox[2],5) # longitudes
m.drawmeridians(meridians,labels=[False,False,False,True],fontsize=12)
m.drawcounties(color='k',zorder=999)

patches   = []
for info, shape in zip(m.layer1_info, m.layer1):
   patches.append( Polygon(np.array(shape), True, color=plt.cm.tab20c(18)) ) # coloring shapefile

pc = PatchCollection(patches, match_original=True, edgecolor='k', linewidths=1., zorder=2)
ax.add_collection(pc)

fig.savefig(shapefile+'_reprojected.png',dpi=300) # save the figure
plt.show()
