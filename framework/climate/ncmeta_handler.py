import json
import logging
import os
from subprocess import (PIPE, Popen,)
from typing import TypedDict

import netCDF4


NCCornerCoordinates = TypedDict(
    "CornerCoordinates",
    {
        "upperLeft": list,
        "lowerLeft": list,
        "upperRight": list,
        "lowerRight": list,
        "center": list,
    },
)

NCExtent = TypedDict("NCExtent", {"type": str, "coordinates": list})

NCBand = TypedDict(
    "NCBand",
    {"index": int, "min": float, "max": float, "NETCDF_DIM_time": str},
    total=False,
)

NCVariable = TypedDict(
    "NCVariable",
    {
        "NETCDF_VARNAME": str,
        "standard_name": str,
        "long_name": str,
        "type": str,
        "unit": str,
    },
    total=False,
)

NCMetaData = TypedDict(
    "NCMetaData",
    {
        "size": list,
        "NETCDF_DIM_time_VALUES": list,
        "time#calendar": str,
        "time#units": str,
        "cornerCoordinates": NCCornerCoordinates,
        "extent": NCExtent,
        "num_bands": int,
        "bands": dict[str, NCBand],
        "varinfo": NCVariable,
    },
)

# Add logging
logger = logging.getLogger('django')


def read_raw_nc_meta_from_file(filepath: str):
    JSON_metadata = None
    try:
        # reading metadata via gdalinfo script
        process = Popen(["gdalinfo", filepath, "-json", "-mm"], stdout=PIPE, stderr=PIPE)
        # process = Popen(f"gdalinfo data/tif_data/{input_filename} -json")
        stdout, stderr = process.communicate()
        metadata = stdout.decode("utf-8")

        JSON_metadata = json.loads(metadata)
        sub_meta = JSON_metadata['metadata']['']
        if 'NETCDF_DIM_time_VALUES' not in sub_meta:
            logger.debug("gdalinfo without var failed: " + filepath)
            raise Exception("NETCDF_DIM_time_VALUES not found in metadata")
        else:
            return JSON_metadata

    except Exception:
        try:
            # Open the NetCDF file
            file = netCDF4.Dataset(filepath, 'r')

            # Print all variable names
            variable_names = list(file.variables.keys())
            # reading metadata via gdalinfo script
            for var in variable_names:
                if var not in ["time", "lat", "lon", "prob_of_zero", "latitude", "longitude", "climatology_bounds", "climatology_bounds_details",
                               "height"] and "time" not in var:
                    process = Popen(["gdalinfo", "NETCDF:" + filepath + ":" + var, "-json", "-mm"], stdout=PIPE, stderr=PIPE)
                    stdout, stderr = process.communicate()
                    metadata = stdout.decode("utf-8")
                    JSON_metadata = json.loads(metadata)
                    logger.debug('fallback used: ' + str(var) + " file:" + filepath)
                    break
            JSON_metadata = json.loads(metadata)
            return JSON_metadata
        except Exception as e:
            logger.error("Error reading metadata: " + filepath + " " + var + " " + str(e))
            return False, "error"


def read_file_specific_metadata(filepath: str):
    # file specific metadata extraction
    file_meta = {
        'st_mtime_nc': "",
        'st_size_nc': ""
    }

    try:
        # this is also used for converted version(s) of the file
        # like tif. when a TempResultFile does not match the
        # st_mtime of the file, the file is not up to date and should
        # probably be deleted
        filestats = os.stat(filepath)
        file_meta['st_mtime_nc'] = filestats.st_mtime
        file_meta['st_size_nc'] = filestats.st_size

        return file_meta
    except Exception:
        return False


def extract_ncfile_metadata(filepath: str):
    raw_meta = read_raw_nc_meta_from_file(filepath)
    if not raw_meta:
        return False, "no raw metadata"

    # obvious checks, if these keys are missing, extraction fails
    if 'metadata' not in raw_meta or 'bands' not in raw_meta:
        return False, "no metadata or bands" + str(raw_meta)

    if '' not in raw_meta['metadata']:
        return False, "no second level metadata"

    if len(raw_meta['bands']) < 0:
        return False, "no bands"

    # nc metadata extraction
    nc_size = None
    if 'size' in raw_meta:
        nc_size = raw_meta['size']

    nc_cornerCoordinates = None
    if 'cornerCoordinates' in raw_meta:
        try:
            nc_cornerCoordinates: NCCornerCoordinates = {
                'upperLeft': raw_meta['cornerCoordinates']['upperLeft'],
                'upperRight': raw_meta['cornerCoordinates']['upperRight'],
                'lowerLeft': raw_meta['cornerCoordinates']['lowerLeft'],
                'lowerRight': raw_meta['cornerCoordinates']['lowerRight'],
                'center': raw_meta['cornerCoordinates']['center']
            }
        except Exception:
            nc_cornerCoordinates = None

    nc_extent = None
    extent_key = False
    if 'extent' in raw_meta:
        extent_key = 'extent'
    elif 'wgs84Extent' in raw_meta:
        extent_key = 'wgs84Extent'

    if extent_key:
        try:
            nc_extent: NCExtent = {
                'type': raw_meta[extent_key]['type'],
                'coordinates': raw_meta[extent_key]['coordinates']
            }
        except Exception:
            nc_extent = None

    # second level metadata
    sub_meta = raw_meta['metadata']['']

    nc_netcdf_times = []
    if 'NETCDF_DIM_time_VALUES' in sub_meta:
        try:
            raw_time_values = sub_meta['NETCDF_DIM_time_VALUES']
            raw_time_values = raw_time_values.replace("{", "").replace("}", "").replace(" ", "")
            nc_netcdf_times = raw_time_values.split(",")
        except Exception:
            return False, "NETCDF_DIM_time_VALUES error"
    else:
        # NOTE - this is a full failure, because time values are always assumed
        return False, "this is a full failure" + str(raw_meta)

    nc_time_calendar = None
    if 'time#calendar' in sub_meta:
        nc_time_calendar = sub_meta['time#calendar']

    nc_time_units = None
    if 'time#units' in sub_meta:
        nc_time_units = sub_meta['time#units']

    bands_meta = raw_meta['bands']
    nc_extracted_bands_meta: dict[str, NCBand] = {}
    try:
        for i, b_meta in enumerate(bands_meta):
            band_collect: NCBand = {}
            if 'computedMin' in b_meta:
                band_collect['min'] = b_meta['computedMin']
            elif 'min' in b_meta:
                band_collect['min'] = b_meta['min']
            else:
                try:
                    if 'valid_min' in b_meta['metadata']['']:
                        band_collect['min'] = b_meta['metadata']['']['valid_min']
                    else:
                        band_collect['min'] = None
                except Exception:
                    continue
                band_collect['min'] = None

            if 'computedMax' in b_meta:
                band_collect['max'] = b_meta['computedMax']
            elif 'max' in b_meta:
                band_collect['max'] = b_meta['max']
            else:
                band_collect['max'] = None

            if 'noDataValue' in b_meta:
                band_collect['noDataValue'] = b_meta['noDataValue']
            else:
                band_collect['noDataValue'] = "NaN"

            band_collect['NETCDF_DIM_time'] = b_meta['metadata'][''][
                'NETCDF_DIM_time'
            ]
            band_collect["index"] = i + 1
            nc_extracted_bands_meta[str(i + 1)] = band_collect
    except Exception as e:
        print(e)
        return False, "missing metadata key,value pairs" + str(e)

    nc_varinfo: NCVariable = {}
    first_band = bands_meta[0]
    if 'type' in first_band:
        nc_varinfo['type'] = first_band['type']
    else:
        nc_varinfo['type'] = None
    try:
        fb_sub = first_band['metadata']['']
        if 'NETCDF_VARNAME' in fb_sub:
            nc_varinfo['NETCDF_VARNAME'] = fb_sub['NETCDF_VARNAME']
        else:
            nc_varinfo['NETCDF_VARNAME'] = None

        if 'standard_name' in fb_sub:
            nc_varinfo['standard_name'] = fb_sub['standard_name']
        else:
            nc_varinfo['standard_name'] = None

        if 'long_name' in fb_sub:
            nc_varinfo['long_name'] = fb_sub['long_name']
        else:
            nc_varinfo['long_name'] = None

        if 'units' in fb_sub:
            nc_varinfo['unit'] = fb_sub['units']
        else:
            nc_varinfo['unit'] = None
    except Exception:
        nc_varinfo['NETCDF_VARNAME'] = None
        nc_varinfo['standard_name'] = None
        nc_varinfo['long_name'] = None
        nc_varinfo['unit'] = None

    full_nc_meta: NCMetaData = {
        'size': nc_size,
        'cornerCoordinates': nc_cornerCoordinates,
        'extent': nc_extent,
        'NETCDF_DIM_time_VALUES': nc_netcdf_times,
        'time#calendar': nc_time_calendar,
        'time#units': nc_time_units,
        'bands': nc_extracted_bands_meta,
        'varinfo': nc_varinfo,
        'num_bands': len(nc_extracted_bands_meta)
    }

    return True, full_nc_meta


def helper_read_and_add_nodatavalue(cur_nc_meta: dict, filepath: str):
    raw_meta = read_raw_nc_meta_from_file(filepath)
    if not raw_meta:
        return False, "no raw metadata"

    # obvious checks, if these keys are missing, extraction fails
    if 'metadata' not in raw_meta or 'bands' not in raw_meta:
        return False, "no metadata or bands" + str(raw_meta)

    if '' not in raw_meta['metadata']:
        return False, "no second level metadata"

    if len(raw_meta['bands']) < 0:
        return False, "no bands"

    bands_meta = raw_meta['bands']
    nc_extracted_bands_meta: dict[str, NCBand] = {}
    try:
        for i, b_meta in enumerate(bands_meta):
            band_collect: NCBand = {}
            if 'computedMin' in b_meta:
                band_collect['min'] = b_meta['computedMin']
            elif 'min' in b_meta:
                band_collect['min'] = b_meta['min']
            else:
                try:
                    if 'valid_min' in b_meta['metadata']['']:
                        band_collect['min'] = b_meta['metadata']['']['valid_min']
                    else:
                        band_collect['min'] = None
                except Exception:
                    continue
                band_collect['min'] = None

            if 'computedMax' in b_meta:
                band_collect['max'] = b_meta['computedMax']
            elif 'max' in b_meta:
                band_collect['max'] = b_meta['max']
            else:
                band_collect['max'] = None

            if 'noDataValue' in b_meta:
                band_collect['noDataValue'] = b_meta['noDataValue']
            else:
                band_collect['noDataValue'] = "NaN"

            band_collect['NETCDF_DIM_time'] = b_meta['metadata'][''][
                'NETCDF_DIM_time'
            ]
            band_collect["index"] = i + 1
            nc_extracted_bands_meta[str(i + 1)] = band_collect
    except Exception as e:
        print(e)
        return False, "missing metadata key,value pairs" + str(e)

    cur_nc_meta['bands'] = nc_extracted_bands_meta

    return cur_nc_meta
