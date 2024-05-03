#! /usr/bin/env python
# -*- coding: utf-8 -*-
from builtins import str
import shapely
from shapely.geometry import shape, box, MultiPolygon
import numpy as np
from collections import Counter
from osgeo import gdal, ogr
from osgeo.gdalconst import GA_ReadOnly
from .utils import bbox_to_pixel_offsets, shapely_to_ogr_type, get_features, \
                   RasterStatsError, raster_extent_as_bounds


if ogr.GetUseExceptions() != 1:
    ogr.UseExceptions()


DEFAULT_STATS = ['count', 'min', 'max', 'mean']
VALID_STATS = DEFAULT_STATS + \
    ['sum', 'std', 'median', 'all', 'majority', 'minority', 'unique', 'range']

# Correspondance entre python2 "basestring" et python3 "str"
try:
  basestring
except NameError:
  basestring = str

def raster_stats(vectors, raster, layer_num=0, band_num=1, nodata_value=None,
                 global_src_extent=False, categorical=False, stats=None,
                 copy_properties=False):

    if not stats:
        if not categorical:
            stats = DEFAULT_STATS
        else:
            stats = []
    else:
        if isinstance(stats, basestring):
            if stats in ['*', 'ALL']:
                stats = VALID_STATS
            else:
                stats = stats.split()
    for x in stats:
        if x not in VALID_STATS:
            raise RasterStatsError("Stat `%s` not valid;" \
                " must be one of \n %r" % (x, VALID_STATS))

    run_count = False
    if categorical or 'majority' in stats or 'minority' in stats or 'unique' in stats or 'all' in stats :
        # run the counter once, only if needed
        run_count = True

    rds = gdal.Open(raster, GA_ReadOnly)
    if not rds:
        raise RasterStatsError("Cannot open %r as GDAL raster" % raster)
    rb = rds.GetRasterBand(band_num)
    rgt = rds.GetGeoTransform()
    rsize = (rds.RasterXSize, rds.RasterYSize)
    rbounds = raster_extent_as_bounds(rgt, rsize)

    if nodata_value is not None:
        nodata_value = float(nodata_value)
        rb.SetNoDataValue(nodata_value)
    else:
        nodata_value = rb.GetNoDataValue()

    features_iter, strategy, spatial_ref = get_features(vectors, layer_num)

    if global_src_extent:
        # create an in-memory numpy array of the source raster data
        # covering the whole extent of the vector layer
        if strategy != "ogr":
            raise RasterStatsError("global_src_extent requires OGR vector")

        # find extent of ALL features
        ds = ogr.Open(vectors)
        layer = ds.GetLayer(layer_num)
        ex = layer.GetExtent()
        # transform from OGR extent to xmin, ymin, xmax, ymax
        layer_extent = (ex[0], ex[2], ex[1], ex[3])

        global_src_offset = bbox_to_pixel_offsets(rgt, layer_extent)
        global_src_array = rb.ReadAsArray(*global_src_offset)

    mem_drv = ogr.GetDriverByName('Memory')
    driver = gdal.GetDriverByName('MEM')

    results = []

    for i, feat in enumerate(features_iter):
        if feat['type'] == "Feature":
            try :
                geom = shape(feat['geometry'])
            except :
                next
        else:  # it's just a geometry
            geom = shape(feat)

        # Point and MultiPoint don't play well with GDALRasterize
        # convert them into box polygons the size of a raster cell
        buff = rgt[1] / 2.0
        if geom.geom_type == "MultiPoint":
            geom = MultiPolygon([box(*(pt.buffer(buff).bounds))
                                for pt in geom.geoms])
        elif geom.geom_type == 'Point':
            geom = box(*(geom.buffer(buff).bounds))

        ogr_geom_type = shapely_to_ogr_type(geom.geom_type)

        # "Clip" the geometry bounds to the overall raster bounding box
        # This should avoid any rasterIO errors for partially overlapping polys
        geom_bounds = list(geom.bounds)
        if geom_bounds[0] < rbounds[0]:
            geom_bounds[0] = rbounds[0]
        if geom_bounds[1] < rbounds[1]:
            geom_bounds[1] = rbounds[1]
        if geom_bounds[2] > rbounds[2]:
            geom_bounds[2] = rbounds[2]
        if geom_bounds[3] > rbounds[3]:
            geom_bounds[3] = rbounds[3]

        # calculate new geotransform of the feature subset
        src_offset = bbox_to_pixel_offsets(rgt, geom_bounds)

        new_gt = (
            (rgt[0] + (src_offset[0] * rgt[1])),
            rgt[1],
            0.0,
            (rgt[3] + (src_offset[1] * rgt[5])),
            0.0,
            rgt[5]
        )

        if src_offset[2] < 0 or src_offset[3] < 0:
            # we're off the raster completely, no overlap at all, so there's no need to even bother trying to calculate
            feature_stats = dict([(s, None) for s in stats])
        else:
            if not global_src_extent:
                # use feature's source extent and read directly from source
                # fastest option when you have fast disks and well-indexed raster
                # advantage: each feature uses the smallest raster chunk
                # disadvantage: lots of disk reads on the source raster
                src_array = rb.ReadAsArray(*src_offset)

                if src_array is None:
                    src_offset = (src_offset[0],src_offset[1],src_offset[2],src_offset[3] - 1)
                    src_array = rb.ReadAsArray(*src_offset)

            else:
                # derive array from global source extent array
                # useful *only* when disk IO or raster format inefficiencies are your limiting factor
                # advantage: reads raster data in one pass before loop
                # disadvantage: large vector extents combined with big rasters need lot of memory
                xa = src_offset[0] - global_src_offset[0]
                ya = src_offset[1] - global_src_offset[1]
                xb = xa + src_offset[2]
                yb = ya + src_offset[3]
                src_array = global_src_array[ya:yb, xa:xb]

            # Create a temporary vector layer in memory
            mem_ds = mem_drv.CreateDataSource('out')
            mem_layer = mem_ds.CreateLayer('out', spatial_ref, ogr_geom_type)
            ogr_feature = ogr.Feature(feature_def=mem_layer.GetLayerDefn())
            ogr_geom = ogr.CreateGeometryFromWkt(geom.wkt)
            ogr_feature.SetGeometryDirectly(ogr_geom)
            mem_layer.CreateFeature(ogr_feature)

            # Rasterize it
            rvds = driver.Create('rvds', src_offset[2], src_offset[3], 1, gdal.GDT_Byte)
            rvds.SetGeoTransform(new_gt)

            gdal.RasterizeLayer(rvds, [1], mem_layer, None, None, burn_values=[1])
            rv_array = rvds.ReadAsArray()
            # Mask the source data array with our current feature
            # we take the logical_not to flip 0<->1 to get the correct mask effect
            # we also mask out nodata values explicitly
            # ATTENTION : probleme possible si src_array == None.

            test_ok = True
            if src_array is None:
                #print("WARNING!!! src_array = "+ str(src_array) + ", nodata_value = " + str(nodata_value))
                test_ok = False
            else :
                # Supprimer les NoData du NumPy array (nouvelle fonction issue de rasterstats v0.19) :
                masked = np.ma.MaskedArray(src_array, mask=(src_array==nodata_value))

            if run_count:
                if test_ok :
                    pixel_count = Counter(masked.compressed())
                else :
                    pixel_count = 0
            if categorical:
                feature_stats = dict(pixel_count)
            else:
                feature_stats = {}

            if 'min' in stats:
                if test_ok and masked.min().any():
                    try :
                        feature_stats['min'] = float(masked.min())
                    except :
                        feature_stats['min'] = 0.0
                else :
                    feature_stats['min'] = 0.0
            if 'max' in stats:
                if test_ok and masked.max().any() :
                    try :
                        feature_stats['max'] = float(masked.max())
                    except :
                        feature_stats['max'] = 0.0
                else :
                    feature_stats['max'] = 0.0
            if 'mean' in stats:
                if test_ok and masked.mean().any():
                    try :
                        feature_stats['mean'] = float(masked.mean())
                    except :
                        feature_stats['mean'] = 0.0
                else :
                    feature_stats['mean'] = 0.0
            if 'count' in stats:
                if test_ok and masked.count().any():
                    try :
                        feature_stats['count'] = int(masked.count())
                    except :
                        feature_stats['count'] = 0
                else :
                    feature_stats['count'] = 0
            # optional
            if 'sum' in stats:
                if test_ok and masked.sum().any():
                    try :
                        feature_stats['sum'] = float(masked.sum())
                    except :
                        feature_stats['sum'] = 0.0
                else :
                    feature_stats['sum'] = 0.0
            if 'std' in stats:
                if test_ok and masked.std().any():
                    try :
                        feature_stats['std'] = float(masked.std())
                    except :
                        feature_stats['std'] = 0.0
                else :
                    feature_stats['std'] = 0.0
            if 'median' in stats:
                if test_ok and masked.compressed().any():
                    try :
                        feature_stats['median'] = float(np.median(masked.compressed()))
                    except :
                        feature_stats['median'] = 0.0
                else :
                    feature_stats['median'] = 0.0

            # Ajout option 'all' GFT le 17/03/2014
            if 'all' in stats:
                try:
                    feature_stats['all'] = pixel_count.most_common()
                except IndexError:
                    feature_stats['all'] = None

            if 'majority' in stats:
                try:
                    feature_stats['majority'] = pixel_count.most_common(1)[0][0]
                except IndexError:
                    feature_stats['majority'] = None

            if 'minority' in stats:
                try:
                    feature_stats['minority'] = pixel_count.most_common()[-1][0]
                except IndexError:
                    feature_stats['minority'] = None

            if 'unique' in stats:
                if test_ok :
                    feature_stats['unique'] = len(pixel_count.keys())
                else :
                    feature_stats['unique'] = 0

            if 'range' in stats:
                try:
                    rmin = feature_stats['min']
                except KeyError:
                    if test_ok and masked.min().any():
                        try:
                            rmin = float(masked.min())
                        except :
                            rmin = 0.0
                    else :
                        rmin = 0.0
                try:
                    rmax = feature_stats['max']
                except KeyError:
                    if test_ok and masked.max().any():
                        try:
                            rmax = float(masked.max())
                        except :
                            rmax = 0.0
                    else :
                        rmax = 0.0
                feature_stats['range'] = rmax - rmin

        try:
            # Use the provided feature id as __fid__
            feature_stats['__fid__'] = feat['id']
        except KeyError:
            # use the enumerator
            feature_stats['__fid__'] = i

        if 'properties' in feat and copy_properties:
            for key, val in feat['properties'].items():
                feature_stats[key] = val

        results.append(feature_stats)

    return results

def stats_to_csv(stats):
    from cStringIO import StringIO
    import csv

    csv_fh = StringIO()

    keys = set()
    for stat in stats:
        for key in stat.keys():
            keys.add(key)

    fieldnames = sorted(list(keys))

    csvwriter = csv.DictWriter(csv_fh, delimiter=',', fieldnames=fieldnames)
    csvwriter.writerow(dict((fn,fn) for fn in fieldnames))
    for row in stats:
        csvwriter.writerow(row)
    contents = csv_fh.getvalue()
    csv_fh.close()
    return contents

