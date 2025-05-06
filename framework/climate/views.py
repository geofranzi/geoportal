import glob
# import grp
import json
# import netCDF4 as nc
import logging
# import mimetypes
import os
# import pwd
import sys
# import cf_xarray as cfxr
import tarfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import netCDF4
import pandas as pd
import requests
import xarray as xr
from django.conf import settings
from django.http import (FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse,)
from elasticsearch_dsl import Index
from elasticsearch_dsl.connections import connections
from osgeo import gdal
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
# import xclim.indices
from xclim import testing

from .graph_db import (activities, base_for_entities, count_prov, result_entities, source_entities,)
from .models import (ClimateLayer, TempResultFile,)
from .ncmeta_handler import (extract_ncfile_metadata, helper_read_and_add_nodatavalue, read_file_specific_metadata,)
from .search_es import (ClimateCollectionSearch, ClimateDatasetsCollectionIndex, ClimateDatasetsIndex,
                        ClimateIndicatorIndex, ClimateIndicatorSearch, ClimateSearch,)
from .serializer import ClimateLayerSerializer
from .temp_file_locations import (JAMS_TMPL_FILE, TEMP_FOLDER_TYPES, URLTXTFILES_DIR, FileInfo, FolderInfo,
                                  copy_filename_as_tif, parse_temp_filename_from_param,
                                  parse_temp_foldertype_from_param, parse_urltxt_filename_from_param, temp_cat_filename,
                                  tmp_cache_path, tmp_raw_filepath, tmp_raw_path,)


logger = logging.getLogger('django')

# GENERAL_API_URL = "http://127.0.0.1:8000/"
GENERAL_API_URL = "https://leutra.geogr.uni-jena.de/backend_geoportal/"
# GENERAL_API_URL = "https://leutra.geogr.uni-jena.de/api/"

HASH_LENGTH = 32  # custom length for temporary .txt files generated during wget request
TEMP_CONVERSION_LIMIT = 75  # filesize limit in MB for conversion (nc -> tif)
TEMP_DOWNLOAD_LIMIT = 1000  # replace and use if needed
TEMP_NUM_BANDS_LIMIT = 4300  # bands limit as number for conversion (nc -> tif)


class TmpCache:
    """Helper class to interact with tmp folder cache.
    """
    _folder_cache: dict[str, FolderInfo] = {}  # folder cache
    _instance = None  # singleton instance helper

    # simple advancable singleton constructor
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TmpCache, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def get_folder_all(self, foldertype):
        """Return content on all files in folder given by foldertype.
        """
        source_dir = tmp_raw_path(foldertype)
        logger.debug(f"source_dir: {source_dir}")
        if not source_dir:
            return []

        return list(self._folder_cache[foldertype]["content"].values())

    def get_folder_convertable(self, foldertype):
        """Return content on all (tif_convertable) files in folder given by foldertype.
        """
        source_dir = tmp_raw_path(foldertype)
        if not source_dir:
            return []

        conv_filtered = {k: v for (k, v) in self._folder_cache[foldertype]["content"].items() if (v["tif_convertable"] and v["filesuffix"] == ".nc")}
        return list(conv_filtered.values())

    def populate_folders(self):
        """Populate key value pairs in folder_cache (only used once after init).
        """
        for foldertype in TEMP_FOLDER_TYPES:
            # check path and cache existence
            if not tmp_raw_path(foldertype) or foldertype in self._folder_cache:
                logger.error(f"Folder {foldertype} not found or already in cache.")
                continue

            folder_info: FolderInfo = {
                'last_update': 0.0,
                'content': {}
            }

            self._folder_cache[foldertype] = folder_info

    def flag_tif_exists(self, foldertype: str, filename: str, value: bool):
        """Flag that a tif file exists (given by foldertype and filename).
        """
        try:
            self._folder_cache[foldertype]["content"][filename]["tif_exists"] = value
        except Exception:
            pass

    def flag_dat_exists(self, foldertype: str, filename: str, value: bool):
        """Flag that a dat file exists (given by foldertype and filename).
        """
        try:
            self._folder_cache[foldertype]["content"][filename]["dat_exists"] = value
        except Exception:
            pass

    def flag_dat_clipped_exists(self, foldertype: str, filename: str, value: bool):
        """Flag that a dat file exists (given by foldertype and filename).
        """
        try:
            self._folder_cache[foldertype]["content"][filename]["dat_clipped_exists"] = value
        except Exception:
            pass

    def flag_nc_clipped_exists(self, foldertype: str, filename: str, value: bool):
        """Flag that a dat file exists (given by foldertype and filename).
        """
        try:
            self._folder_cache[foldertype]["content"][filename]["nc_clipped_exists"] = value
        except Exception:
            pass

    def is_foldercontent_empty(self, foldertype: str) -> bool:
        """Check if folder has been loaded yet. Used for lazy loading.
        """
        try:
            if len(self._folder_cache[foldertype]["content"]) == 0:
                return True
            else:
                return False
        except Exception:
            return False

    def update_by_foldertype(self, foldertype: str):
        """Reload folder in cache. If new files are found, try to read them to
        database. Time gated.
        """
        source_dir = tmp_raw_path(foldertype)

        try:
            foldercontent, dat_files, dat_clipped_files, nc_clipped_files = read_folder_constrained(source_dir)
        except Exception as e:
            print(f"Could not read from folder {source_dir} {e}")
            # return HttpResponse(content="Reading the content of the selected folder has failed.", status=500)
            return False

        try:
            # time gate
            if abs(self._folder_cache[foldertype]["last_update"] - time.time()) <= 5.0:
                print("Update locked by time gate: ", abs(self._folder_cache[foldertype]["last_update"] - time.time()))
                return False
            self._folder_cache[foldertype]["last_update"] = time.time()
        except Exception:
            return False

        # used to collect data on each file
        all_files = dict.fromkeys(foldercontent, None)

        # helper for the database filter
        cat_helper = []
        for f in foldercontent:
            cat_helper.append(temp_cat_filename(foldertype, f))

        # filter and read fileinfo from database (if available)
        for f_res in TempResultFile.objects.filter(categorized_filename__in=cat_helper):
            if f_res.filename in all_files:
                all_files[f_res.filename] = f_res

        # whole folder with fileinfo on each file (from db)
        content: dict[str, FileInfo] = {}

        # assemble FileInfo from all files
        for i, f in enumerate(foldercontent):
            if all_files[f] is None:
                # db creation routine
                succ, msg = extract_ncfile(f, foldertype)
                if succ:
                    all_files[f] = msg
                pass

            filepath = tmp_raw_filepath(foldertype, f)

            try:
                file_stats = os.stat(filepath)
                creation_date = None
                creation_date = datetime.fromtimestamp(file_stats.st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                )
                filename = f
                filesize = sizeof_fmt(file_stats.st_size)
                in_limit_conversion = in_sizelimit_conversion_i(file_stats.st_size)
                in_limit_download = in_sizelimit_download_i(file_stats.st_size)
                filesuffix = Path(f).suffix

                dirty = True
                num_bands = -1
                # what we know from database
                f_info: TempResultFile = all_files[f]
                if f_info is not None:
                    fileversion = f_info.st_mtime_nc
                    if fileversion == str(file_stats.st_mtime):
                        dirty = False
                    tif_exists = has_tif_file(f_info.filename, foldertype, f_info)
                    # convertability
                    if not tif_exists:
                        conv_constraint = is_tif_convertable(f_info.filename, foldertype, f_info)
                        tif_convertable = conv_constraint
                    else:
                        tif_convertable = True
                    if f_info.nc_meta and 'num_bands' in f_info.nc_meta:
                        num_bands = f_info.nc_meta['num_bands']
                else:
                    tif_exists = False
                    tif_convertable = False
                    fileversion = str(file_stats.st_mtime)

                if (f + ".dat" in dat_files):
                    dat_exists = True
                else:
                    dat_exists = False

                if (f.replace(".nc", "_clipped.nc.dat") in dat_clipped_files):
                    dat_clipped_exists = True
                else:
                    dat_clipped_exists = False

                if (f.replace(".nc", "_clipped.nc") in nc_clipped_files):
                    nc_clipped_exists = True
                else:
                    nc_clipped_exists = False

                content_el: FileInfo = {
                    "filename": filename,
                    "filesize": filesize,
                    "filesuffix": filesuffix,
                    "creation_date": creation_date,
                    "fileversion": fileversion,
                    "dat_exists": dat_exists,
                    "dat_clipped_exists": dat_clipped_exists,
                    "nc_clipped_exists": nc_clipped_exists,
                    "tif_exists": tif_exists,
                    "tif_convertable": tif_convertable,
                    "dirty": dirty,
                    "in_limit_conversion": in_limit_conversion,
                    "in_limit_download": in_limit_download,
                    "num_bands": num_bands

                }
                content[f] = content_el
            except Exception as e:
                # file could not be read (this should only ever happen when
                # serverfiles and folder_content go out of sync)
                print("Fileread ERR while processing FolderContent request:\n", e)
                continue

        try:
            # update value in cache
            self._folder_cache[foldertype]["content"] = content
            return True
        except Exception:
            return False


tmp_cache = TmpCache()
tmp_cache.populate_folders()

print(f"The settings DEBUG settings is: {settings.DEBUG}")


# SPECIFICATIONS [temp results]
#  - download single file
#      - as .nc, .tif
#      - .tif needs version check, and thus database entry
#      - .tif may need to be generated, thus needs metadata check
#  - download multiple files
#      - same requirements as single file BUT
#      - possibly many .tif files need generating and database accesses

#  - display content of one specific temp result folder
#      - collect filenames, stats, filechange-date, (..)
#      - used for frontend visualisation
#      - mostly done, only adaptations

#  - select filenames for wget script, to be saved in a txt file
#      - needs safe file selection and hashing of the txt file
#      - done, only adaptations

#  - route that returns a txt file (for usage in wget script)
#      - part of a 2 steps process to remember and serve filenames from a hashed txt
#      - mostly done, only adaptations

# 3 Main Functionalities:
#  - 1. properly/safely handling foldertype and filename request parameters
#       and providing cleaned paths for file access
#  - 2. easy access point to read the filenames corresponding db object
#       ( metadata, versioncheck, ..)
#  - 3. serve and maybe generate first -> file for download


@api_view(["GET"])
def serve_static_file_with_cors(request, filename):
    # Construct the full file path based on STATICFILES_DIRS
    static_dir = settings.STATICFILES_DIRS[0]
    print("ROOT: ", static_dir)
    filepath = os.path.join(static_dir, 'cache/water_budget', filename)
    print("PATH: ", filepath)
    if os.path.exists(filepath):
        # File exists, serve it
        response = FileResponse(open(filepath, 'rb'), content_type='image/tiff')
        response["Access-Control-Allow-Origin"] = "*"  # Add CORS header
        return response
    # File not found, raise 404
    return HttpResponse("File not found")


def in_sizelimit_conversion(filepath: str):
    size = (os.stat(filepath).st_size / 1024) / 1024  # MB
    if size > TEMP_CONVERSION_LIMIT:
        return False
    else:
        return True


def in_sizelimit_download(filepath: str):
    size = (os.stat(filepath).st_size / 1024) / 1024  # MB
    if size > TEMP_DOWNLOAD_LIMIT:
        return False
    else:
        return True


def in_sizelimit_conversion_i(st_size: int):
    size = (st_size / 1024) / 1024  # MB
    if size > TEMP_CONVERSION_LIMIT:
        return False
    else:
        return True


def in_sizelimit_download_i(st_size: int):
    size = (st_size / 1024) / 1024  # MB
    if size > TEMP_DOWNLOAD_LIMIT:
        return False
    else:
        return True


def convert_nc_to_tif(filename_in: str, foldertype: str, temp_doc: TempResultFile) -> tuple[bool, str]:
    """Tries to create a tif from a nc file in a specific folder.
    Tif will be written to tmp_cache_path(foldertype).

    filename_in -- nc filename (input file)
    foldertype -- foldertype from TEMP_FOLDER_TYPES
    temp_doc -- TempResultFile object of the input file

    :return: tuple[bool, str] ... ([success, contextmessage])
    """
    filepath_in = tmp_raw_filepath(foldertype, filename_in)
    if not filepath_in:
        return False, "No raw file"

    if not in_sizelimit_conversion(filepath_in):
        return False, "Raw file too big"

    if temp_doc.nc_meta['num_bands'] is None:
        return False, "Could not convert to tif because of missing metadata"

    if not is_tif_convertable(filename_in, foldertype, temp_doc):
        return False, "Raw file not tif convertable"

    filename_out = copy_filename_as_tif(filename_in)
    filepath_out = tmp_cache_path(foldertype, filename_out)

    if not filepath_out:
        return False, "Invalid path to output file"

    # Set destination spatial reference
    kwargs = {"dstSRS": 'EPSG:4326'}

    try:
        # for some reason, tif files created via translate are
        # not allways working correctly in our visualization (thatswhy Warp)
        # gdal.PushErrorHandler(gdal.CPLQuietErrorHandler)  # Suppress direct print
        gdal_res = gdal.Warp(filepath_out, filepath_in, **kwargs)
        # gdal.PopErrorHandler()  # Restore normal error handling

        # if gdal fails it returns none, and automatically write the error with the
        # associated filepath to console (this should appear in our error.log)
        if gdal_res is None:
            # last_error = gdal.GetLastErrorMsg()  # Get the last error message
            # return False, "Gdal Warp to tif failed with error: "  # + last_error
            # throw Exception("Gdal Warp to tif failed with error: " + last_error)
            # enforce Exception to be thrown
            raise Exception("Gdal Warp to tif failed with error: ")

        fileversion_out = os.stat(filepath_out).st_mtime
        temp_doc.st_mtime_tif = fileversion_out
        temp_doc.save()
        return True, ""
    except Exception:
        try:
            file = netCDF4.Dataset(filepath_in, 'r')

            # Print all variable names
            variable_names = list(file.variables.keys())
            for var in variable_names:
                if var not in ["time", "lat", "lon", "prob_of_zero", "latitude",
                               "longitude", "climatology_bounds_details", "climatology_bounds", "height"] and "time" not in var:
                    gdal_res = gdal.Warp(filepath_out, "NETCDF:" + filepath_in + ":" + var, **kwargs)
                    fileversion_out = os.stat(filepath_out).st_mtime
                    temp_doc.st_mtime_tif = fileversion_out
                    temp_doc.save()
                    logger.error('fallback used: ' + str(var) + " file:" + filepath_in)
                    return True, ""

        except Exception as e:
            last_error = gdal.GetLastErrorMsg()
            logger.error('Gdal Translate to tif failed with error: ' + str(var) + " file:" + filepath_in + " " + str(e) + " " + last_error)
            return False, "Gdal Translate to tif failed with error: " + str(e) + " " + last_error
        return False, "Conversion failed"


def has_tif_file(raw_filename: str, foldertype: str, temp_doc: TempResultFile) -> bool:
    """Checks if a up-to-date tif file exists for a corresponding nc file.
    """
    tif_filename = copy_filename_as_tif(raw_filename)
    tif_path = os.path.join(tmp_cache_path(foldertype), tif_filename)

    if not os.path.isfile(tif_path):
        return False

    tif_version = os.stat(tif_path).st_mtime
    if not temp_doc.check_cache_version(tif_version):
        return False

    # file exists, and version matches
    return True


def is_tif_convertable(raw_filename: str, foldertype: str, temp_doc: TempResultFile) -> bool:
    """Checks if our custom constraints for (nc -> tif) file conversion are met. It might still
    happen that conversion fails (e.g. we have no metadata yet and only assume it's possible).
    """
    filepath = tmp_raw_filepath(foldertype, raw_filename)
    if not filepath or not in_sizelimit_conversion(filepath):
        return False

    # TODO: - change this to cover all cases
    if temp_doc.nc_meta['num_bands'] is None or temp_doc.nc_meta['num_bands'] > TEMP_NUM_BANDS_LIMIT:
        return False
    else:
        return True


def extract_ncfile_lite(filename: str, foldertype: str, force_update=False):
    """Read filesize and creation time from a file and create/update the specific TempResultFile.

    :return: tuple[bool, str|TempResultFile]
             on success [true, TempResultFile]
             on failure [false, str]
    """
    cat_filename = temp_cat_filename(foldertype, filename)
    filepath = tmp_raw_filepath(foldertype, filename)
    if not filepath:
        return False, "file not found"

    st_mtime_nc = None
    try:
        # this is also used for converted version(s) of the file
        # like tif. when a TempResultFile does not match the
        # st_mtime of the file, the file is not up to date and should
        # probably be deleted
        filestats = os.stat(filepath)
        st_mtime_nc = filestats.st_mtime
        st_size_nc = filestats.st_size
    except Exception:
        return False, "could not read file stats"

    try:
        old_doc: TempResultFile = TempResultFile.get_by_cat_filename(cat_filename)
        # check if a database object for that file already exists
        if old_doc is not None:
            # if version mismatch or force_update -> delete object
            if force_update or not old_doc.check_raw_version(st_mtime_nc):
                old_doc.delete()
    except Exception:
        pass

    new_doc = None
    try:
        # lite creation (without metadata and tif file)
        new_doc = TempResultFile(
            categorized_filename=cat_filename,
            filename=filename,
            st_mtime_nc=st_mtime_nc,
            st_size_nc=st_size_nc,
            category=foldertype
        )
        new_doc.save()
    except Exception as e:
        print(e)
        return False, "could not save file metadata to database"

    return True, new_doc


def extract_ncfile_to_tmpresult(filename: str, foldertype: str, force_update=False):
    """Tries to read all metadata necessary to us from a nc file and create/update the specific TempResultFile.
    This function HAS NO explicit check for filesize as it would double check in all cases. ONLY USE for files
    that are IN SIZE LIMIT.

    :return: tuple[bool, str|TempResultFile]
            on success [true, TempResultFile]
            on failure [false, str]
    """
    # filename with category prefix, unique over all TempResultFiles
    cat_filename = temp_cat_filename(foldertype, filename)

    filepath = tmp_raw_filepath(foldertype, filename)
    if not filepath:
        return False, "file not found"

    file_meta = read_file_specific_metadata(filepath)

    if not file_meta:
        return False, "no file_meta"

    try:
        old_doc: TempResultFile = TempResultFile.get_by_cat_filename(cat_filename)
        # check if a database object for that file already exists
        if old_doc is not None:
            # if version mismatch or force_update -> delete object
            if not old_doc.check_raw_version(file_meta['st_mtime_nc']) or force_update:
                old_doc.delete()
    except Exception:
        pass

    succ, nc_meta = extract_ncfile_metadata(filepath)
    if not succ:
        # TODO - handling
        # print(f"NC Metadata extraction failed for file: {filepath}")
        return False, "no nc_meta 2" + str(nc_meta) + str(succ)

    new_doc = None
    try:
        new_doc = TempResultFile(
            categorized_filename=cat_filename,
            filename=filename,
            nc_meta=nc_meta,
            st_mtime_nc=file_meta['st_mtime_nc'],
            st_size_nc=file_meta['st_size_nc'],
            category=foldertype,
        )
        new_doc.save()
    except Exception as e:
        print(e)
        return False, "could not save file metadata to database"

    return True, new_doc


def extract_ncfile(filename, foldertype):
    """
    Checks if a .nc file exists and then reads it into database as a
    TempResultFile or lite if size_limit conversion is exceeded.
    """
    filepath = tmp_raw_filepath(foldertype, filename)
    if not filepath:
        return False

    if not in_sizelimit_conversion(filepath):
        succ, msg = extract_ncfile_lite(filename, foldertype)
        return succ, msg
    else:
        succ, msg = extract_ncfile_to_tmpresult(filename, foldertype)
        return succ, msg


def read_folder_constrained(source_dir: str):
    foldercontent_nc = list((file for file in os.listdir(source_dir) if (os.path.isfile(os.path.join(source_dir, file)))))
    try:
        foldercontent_nc_clipped = list(
            (file for file in os.listdir(os.path.join(source_dir, "nc_clipped")) if (os.path.isfile(os.path.join(source_dir, "nc_clipped", file)))))
    except Exception as e:
        logger.debug(f"During read folder constrained: error while reading nc_clipped: {e}")
        foldercontent_nc_clipped = []
    # check if dat folder exists and create if not
    if not os.path.exists(os.path.join(source_dir, "dat")):
        os.makedirs(os.path.join(source_dir, "dat"))
    try:
        foldercontent_dat = list((file for file in os.listdir(os.path.join(source_dir, "dat")) if (os.path.isfile(os.path.join(source_dir, "dat", file)))))
    except Exception as e:
        logger.debug(f"During read folder constrained: error while reading dat: {e}")
        foldercontent_dat = []
    # check if dat_clipped folder exists
    try:
        foldercontent_dat_clipped = list(
            (file for file in os.listdir(os.path.join(source_dir, "dat_clipped")) if (os.path.isfile(os.path.join(source_dir, "dat_clipped", file)))))
    except Exception as e:
        logger.debug(f"During read folder constrained: error while reading dat_clipped: {e}")
        foldercontent_dat_clipped = []

    nc_files = split_files_by_extension(foldercontent_nc, ".nc")
    dat_files = split_files_by_extension(foldercontent_dat, ".dat")
    dat_files_clipped = split_files_by_extension(foldercontent_dat_clipped, "_clipped.nc.dat")
    nc_files_clipped = split_files_by_extension(foldercontent_nc_clipped, "_clipped.nc")
    return nc_files, dat_files, dat_files_clipped, nc_files_clipped


def split_files_by_extension(file_list, filetype):
    # Initialize two empty lists to store files based on their extensions
    nc_files = []
    # Loop through each file in the input list
    for file in file_list:
        # Check if the file ends with '.nc' and add it to the nc_files list
        if file.endswith(filetype):
            nc_files.append(file)
    # Return both lists
    return nc_files


def extract_jams_files(foldertype, filename):
    try:
        import rioxarray  # noqa
        logger.debug('extract jams started')
        wrong_variables = ['time_bnds', 'spatial_ref']
        decimal_digits = 5
        source_dir = tmp_raw_path(foldertype)
        filepath = os.path.join(source_dir, filename)
        try:
            nc = xr.open_dataset(filepath)
        except Exception as e:
            logger.debug(f"During extract jams file: error while reading nc: {e}")
        except MemoryError:
            logger.debug("During extract jams file: memory error")
        i = 0
        epsg_utm = get_utm_epsg_from_nc(filepath)
        var_name = list(nc.data_vars)[i]
        while var_name in wrong_variables:
            i += 1
            var_name = list(nc.data_vars)[i]
        try:
            var_unit = nc[var_name].attrs['units']
        except Exception as e:
            logger.debug(f"During extract jams file: error while parsing units: {e}")
            var_unit = 'none'

        ds = nc[var_name]
        ds = ds.rio.write_crs("EPSG:4326")
        ds = ds.rio.reproject(epsg_utm)
        time_var = nc['time']
        tres = pd.TimedeltaIndex(time_var.diff(dim='time')).mean()
        one_day = pd.Timedelta(days=1)

        df = ds.to_dataframe().reset_index()
        df = df.dropna(subset=[var_name])
        df = df.sort_values(by=['time', 'y', 'x'])
        unique_x_y_pairs = df[['x', 'y']].drop_duplicates()
        unique_times = df['time'].unique()
        min_time = min(unique_times)
        max_time = max(unique_times)

        # read file header template
        try:
            with open(JAMS_TMPL_FILE, "r") as file:
                meta = file.read()
        except Exception as e:
            logger.debug(f"During extract jams file: error while reading jams template: {e}")

        # create metadata header
        meta = meta.replace('%crs%', epsg_utm)
        # meta = ""
        meta = meta.replace('%ncfile%', filename)
        # meta = meta.replace('%shapefile%', shapefile)
        meta = meta.replace('%var_name%', var_name)
        meta = meta.replace('%var_unit%', var_unit)
        meta = meta.replace('%min_time%', str(min_time))
        meta = meta.replace('%max_time%', str(max_time))
        meta = meta.replace('%tres%', 'm' if one_day < tres else 'd')

        stations = ''
        ids = ''
        elevations = ''
        cols = ''
        xs = ''
        ys = ''
        n = 1
        for x, y in unique_x_y_pairs.values:
            stations += 'station_{}\t'.format(n)
            ids += '{}\t'.format(n)
            cols += '{}\t'.format(n)
            elevations += '0.0\t'
            xs += '{}\t'.format(x)
            ys += '{}\t'.format(y)
            n += 1
        meta = meta.replace('%stations%', stations)
        meta = meta.replace('%ids%', ids)
        meta = meta.replace('%elevations%', elevations)
        meta = meta.replace('%cols%', cols)
        meta = meta.replace('%xs%', xs)
        meta = meta.replace('%ys%', ys)
        df.set_index('time', inplace=True)
        # output metadata and data to file
        try:
            with open(r'{}.dat'.format(os.path.join(source_dir, "dat", filename)), 'w', encoding="utf-8") as file:
                # Append lines to the file
                file.write(meta)

                for timestep in unique_times:
                    data = df.loc[timestep]
                    values_list = ['{:.{}f}'.format(value, decimal_digits) for value in data[var_name]]
                    values = '\t'.join(values_list)
                    line = '{}\t{}\n'.format(timestep, values)
                    file.write(line)

                file.write('# end of file')
                file.close()
        except Exception as e:
            logger.debug(f"During extract jams file: error while writing dat-file: {e}")

        tmp_cache.flag_dat_exists(foldertype, filename, True)
        logger.debug('extract jams ended')
    except Exception as unexpected_error:
        logger.debug(f"During extract jams file: unexpected error: {unexpected_error}")


def get_utm_epsg_from_nc(nc_path):
    """
    Reads a NetCDF file and returns the appropriate UTM EPSG code based on its extent.

    Parameters:
        nc_path (str): Path to the NetCDF file

    Returns:
        tuple: (zone_number, hemisphere, epsg_code)
    """
    # Open the NetCDF dataset
    ds = xr.open_dataset(nc_path)

    lon = ds['lon']
    lat = ds['lat']

    # Get min and max values
    min_lon = float(lon.min())
    max_lon = float(lon.max())
    min_lat = float(lat.min())
    max_lat = float(lat.max())

    # Compute center of bounding box
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2

    # Calculate UTM zone
    zone_number = int((center_lon + 180) / 6) + 1
    hemisphere = 'north' if center_lat >= 0 else 'south'

    # EPSG code (32600 + zone for north, 32700 + zone for south)
    epsg_code = 32600 + zone_number if hemisphere == 'north' else 32700 + zone_number
    epsg_code = "EPSG:"+str(epsg_code)
    return epsg_code


@api_view(["GET"])
def access_tif_from_ncfile(request):
    foldertype = parse_temp_foldertype_from_param(request.GET.get("type", default=None))
    filename = parse_temp_filename_from_param(request.GET.get("name", default=None), foldertype)

    if foldertype is False or filename is False:
        err_msg = "Invalid"
        if not foldertype:
            err_msg += " foldertype"
        if not filename:
            err_msg += " filename"

        return HttpResponse(content=err_msg, status=400)

    filepath = tmp_raw_filepath(foldertype, filename)

    # explicit filesize check
    if not in_sizelimit_conversion(filepath):
        return HttpResponse(content="Could not extract raw file metadata. Reason: File too big", status=500)

    cat_filename = temp_cat_filename(foldertype, filename)
    temp_doc: TempResultFile = TempResultFile.get_by_cat_filename(cat_filename)

    # indicates that the database entry for current file
    # needs to be updated
    update_doc = False
    if temp_doc is None:
        update_doc = True
    else:
        fileversion = os.stat(filepath).st_mtime
        if not temp_doc.check_raw_version(fileversion):
            update_doc = True

    if update_doc:
        succ, msg = extract_ncfile_to_tmpresult(filename, foldertype, force_update=True)
        if not succ:
            # could not extract raw file metadata ...
            # thus can not properly translate to tif
            return HttpResponse(content=f"Could not extract raw file metadata. Reason: {msg}", status=500)

        temp_doc: TempResultFile = TempResultFile.get_by_cat_filename(cat_filename)
        if temp_doc is None:
            # could not extract raw file metadata ...
            # thus can not properly translate to tif
            return HttpResponse(content="Could not extract raw file metadata", status=500)

    # indicates that the corresponding tif file
    # needs to be updated/recreated
    update_tif = update_doc
    if not has_tif_file(filename, foldertype, temp_doc):
        update_tif = True

    if update_tif:
        succ, msg = convert_nc_to_tif(filename, foldertype, temp_doc)
        if not succ:
            # The raw file could not be converted
            # print(f"The raw file could not be converted. Reason: {msg}")
            return HttpResponse(content=f"The raw file could not be converted. Reason: {msg}", status=500)

    # if we succeed in returning the tif file, it must exist -> flag it
    tmp_cache.flag_tif_exists(foldertype, filename, True)

    tif_filename = copy_filename_as_tif(filename)

    data = {
        'filename': tif_filename,

        # hardcoded for now, because i'm not absolutely sure on the format
        # TODO: - replace domain and path with variable
        # 'route': f"http://127.0.0.1:8000/static/data/tmp/cache/{foldertype}/{tif_filename}"
        'route': f"https://leutra.geogr.uni-jena.de/tippecc_data/tippecctmp/{foldertype}/{tif_filename}"
    }

    return JsonResponse({'filedata': data})


@api_view(["GET"])
def get_ncfile_metadata(request):
    foldertype = parse_temp_foldertype_from_param(request.GET.get("type", default=None))
    filename = parse_temp_filename_from_param(request.GET.get("name", default=None), foldertype)

    if foldertype is False or filename is False:
        err_msg = "Invalid"
        if not foldertype:
            err_msg += " foldertype"
        if not filename:
            err_msg += " filename"

        return HttpResponse(content=err_msg, status=400)

    filepath_in = tmp_raw_filepath(foldertype, filename)
    fileversion = os.stat(filepath_in).st_mtime

    if not filepath_in:
        return HttpResponse(content="File does not exist", status=500)

    cat_filename = temp_cat_filename(foldertype, filename)
    temp_doc: TempResultFile = TempResultFile.get_by_cat_filename(cat_filename)

    if not in_sizelimit_conversion(filepath_in):
        return HttpResponse(content="File too big to extract metadata", status=500)

    # file does not exist in database
    if temp_doc is None:
        succ, msg = extract_ncfile_to_tmpresult(filename, foldertype)
        if succ:
            new_doc: TempResultFile = msg
            return JsonResponse({'metadata': new_doc.get_file_metadata()})
        else:
            return HttpResponse(content="Could not extraxt metadata from file.", status=500)
    elif not temp_doc.check_raw_version(fileversion):
        # version check
        succ, msg = extract_ncfile_to_tmpresult(filename, foldertype)
        if succ:
            new_doc: TempResultFile = msg
            return JsonResponse({'metadata': new_doc.get_file_metadata()})
        else:
            return HttpResponse(content="Could not extraxt metadata from file.", status=500)

    metadata = temp_doc.get_file_metadata()
    response = JsonResponse({'metadata': metadata})

    return response


@api_view(["GET"])
def get_temp_urls(request):
    """Returns a selected txt file with file urls for usage in wget script.
    Request params:
    hash -- urltxt filename (without .txt ending) as 32 char hash value
    """
    hashed_filename = parse_urltxt_filename_from_param(request.GET.get("hash", default=None))
    if not hashed_filename:
        return HttpResponse(content="Either invalid hash or your selection got deleted.", status=400)

    file_path = os.path.join(URLTXTFILES_DIR, hashed_filename)

    try:
        with open(file_path, "r") as file:
            content = file.read()
        response = StreamingHttpResponse(content)
        response["Content-Type"] = "text/plain; charset=utf8"

        return response
    except Exception as e:
        print(e)
        return HttpResponse(content="Your file selection either got deleted or corrupted.", status=400)


@api_view(["POST"])
def select_temp_urls(request):
    """Reads and saves client requested temp result filenames into txt,
    and returns according wget request string to download the selection
    (download handled by other route)
    Request params:
    type         -- requested file category/subfolder
    request body -- requested filenames
    """
    body_unicode = request.body.decode("utf-8")
    body = json.loads(body_unicode)
    if len(body) == 0:
        return HttpResponse(content="No Files chosen", status=400)
    foldertype = parse_temp_foldertype_from_param(request.GET.get("type", default=None))
    if not foldertype:
        return HttpResponse(content="Invalid foldertype", status=400)

    source_dir = tmp_raw_path(foldertype)
    if not source_dir:
        return HttpResponse(content="Selected folder does currently not exist and cant be accessed.", status=500)

    foldercontent = os.listdir(source_dir)

    # print(foldercontent)

    url_content = ""
    # for all requested files in requestbody, check if they really exist
    for requested_file in body:
        filename = None
        try:
            idx = foldercontent.index(requested_file[0])
            filetype = requested_file[1]
            filename = foldercontent[idx]
            if filetype not in ['tif', 'nc_clipped', 'dat_clipped', 'dat']:
                # reset filetype to actual filename suffix
                # initial parameter only used if client wants to download format A as format B
                # (e.g. .nc as .tif)
                filetype = Path(filename).suffix[1:]

            url_content += (
                    GENERAL_API_URL
                    + "climate/get_temp_file?name="
                    + filename
                    + "&type="
                    + foldertype
                    + "&filetype="
                    + filetype
                    + "\n"
            )
        except Exception as e:
            print(e)
            # one of the requested filenames did not match an actual filename
            return HttpResponse(content=f"Requested filename: {requested_file[0]} does not exist.", status=400)

    unique_filehash = str(uuid.uuid4().hex)
    unique_filename = unique_filehash + ".txt"

    try:
        with open(os.path.join(URLTXTFILES_DIR, unique_filename), "w") as file:
            file.write(url_content)
    except Exception as e:
        print(e)
        return HttpResponse(content="Something went wrong when saving your selection", status=500)

    response = JsonResponse(
        {
            "wget-command": "wget --content-disposition --input-file "
                            + f'"{GENERAL_API_URL}climate/get_temp_urls?hash={unique_filehash}"'
        }
    )

    return response


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0

    return f"{num:.1f}Yi{suffix}"


class FolderContentView(APIView):
    def get(self, request):
        """Returns formated folder content of one of the temp result file subfolders.
        Request params:
        type -- requested file category/subfolder (to display)
        force_update -- If true -> forces folder to update before returning content.
        """
        foldertype = parse_temp_foldertype_from_param(request.GET.get("type", default=None))

        # overly cautious check for folder existence
        source_dir = tmp_raw_path(foldertype)
        if not source_dir:
            return HttpResponse(content="Selected folder does currently not exist and cant be accessed.", status=500)

        force_update = request.GET.get("force_update", default=False)
        if force_update:
            force_update = True

        if not foldertype:
            return HttpResponse(content="Invalid foldertype", status=400)

        only_convertable = request.GET.get("convertable", default=False)
        if only_convertable:
            only_convertable = True

        # update the selected folder if necessary (explicit OR lazy)
        if force_update or tmp_cache.is_foldercontent_empty(foldertype):
            tmp_cache.update_by_foldertype(foldertype)

        if only_convertable:
            content = tmp_cache.get_folder_convertable(foldertype)
            return JsonResponse({"content": content})
        else:
            content = tmp_cache.get_folder_all(foldertype)
            return JsonResponse({"content": content})


class TempDownloadView(APIView):
    def get(self, request):
        """Serves a single file from the temporary result files (for download).
        Request params:
        type -- requested file category/subfolder
        name -- requested filename
        filetype -- requested filetype
        """
        foldertype = parse_temp_foldertype_from_param(request.GET.get("type", default=None))
        filename = parse_temp_filename_from_param(request.GET.get("name", default=None), foldertype)

        # only used for comparison now and thus can be safely used
        filetype = request.GET.get("filetype", default=None)

        if not foldertype or not filename or not filetype:
            err_msg = "Invalid"
            if not foldertype:
                err_msg += " foldertype"
            if not filename:
                err_msg += " filename"
            if not filetype:
                err_msg += " filetype"

            return HttpResponse(content=err_msg, status=400)

        source_dir = tmp_raw_path(foldertype)
        filepath = tmp_raw_filepath(foldertype, filename)

        # important explicit check for filesize before trying to serve
        # deactivate limit, as it prevents also the allowed download for prov and meta
        # if not in_sizelimit_download(filepath):
        #    return HttpResponse(content="Requested file is too big.", status=400)

        # TODO:
        #   - normalize this (remove all hardcoded pathing/filenaming)
        if filetype == 'tif':
            return self.serve_tif_file(filepath, filename, foldertype)
        elif filetype == 'dat':
            if not in_sizelimit_download(filepath):
                return HttpResponse(content="Requested file is too big.", status=400)
            return self.serve_file(os.path.join(source_dir, "dat", filename + '.dat'), filename + '.dat')
        elif filetype == 'meta':
            return self.serve_file(os.path.join(source_dir, "meta", filename).replace(".nc", "_metadata.json"), filename.replace(".nc", "_metadata.json"))
        elif filetype == 'prov':
            return self.serve_file(os.path.join(source_dir, "prov", filename).replace(".nc", "_prov.json"), filename.replace(".nc", "_prov.json"))
        elif filetype == 'prov_stats':
            return self.prov_stats(filename)
        elif filetype == 'nc_clipped':
            return self.serve_file(os.path.join(source_dir, "nc_clipped", filename).replace(".nc", "_clipped.nc"), filename.replace(".nc", "_clipped.nc"))
        elif filetype == 'dat_clipped':
            return self.serve_file(os.path.join(source_dir, "dat_clipped", filename).replace(".nc", "_clipped.nc.dat"),
                                   filename.replace(".nc", "_clipped.nc.dat"))
        else:
            return self.serve_file(filepath, filename)

    def serve_file(self, filepath, filename):
        # ==== this is for local testing

        # just for reference:
        # this -> content_type='application/octet-stream' fixed the decode error

        response = None
        # check if file exists
        if not os.path.isfile(filepath):
            return HttpResponse(content="File does not exist", status=404)
        # check if file is empty
        if os.stat(filepath).st_size == 0:
            return HttpResponse(content="File is empty", status=404)

        else:

            with open(filepath, "rb") as test_file:
                response = HttpResponse(content=test_file.read(), content_type='application/octet-stream')
                response["Content-Disposition"] = f'attachment; filename="{filename}"'

            if response is not None:
                return response
            else:
                return HttpResponse(content="Could not read the file content", status=404)
        # ====

    def serve_tif_file(self, filepath, filename, foldertype):
        cat_filename = temp_cat_filename(foldertype, filename)
        temp_doc: TempResultFile = TempResultFile.get_by_cat_filename(cat_filename)

        # indicates that the database entry for current file
        # needs to be updated
        update_doc = False
        if temp_doc is None:
            update_doc = True
        else:
            fileversion = os.stat(filepath).st_mtime
            if not temp_doc.check_raw_version(fileversion):
                update_doc = True

        if update_doc:
            succ, msg = extract_ncfile_to_tmpresult(filename, foldertype, force_update=True)
            if not succ:
                # could not extract raw file metadata ...
                # thus can not properly translate to tif
                return HttpResponse(content=f"Could not extract raw file metadata. Reason: {msg}", status=500)

            temp_doc: TempResultFile = TempResultFile.get_by_cat_filename(cat_filename)
            if temp_doc is None:
                # could not extract raw file metadata ...
                # thus can not properly translate to tif
                return HttpResponse(content="Could not extract raw file metadata", status=500)

        # indicates that the corresponding tif file
        # needs to be updated/recreated
        update_tif = update_doc
        if not has_tif_file(filename, foldertype, temp_doc):
            update_tif = True

        if update_tif:
            succ, msg = convert_nc_to_tif(filename, foldertype, temp_doc)
            if not succ:
                # The raw file could not be converted
                # print(f"The raw file could not be converted. Reason: {msg}")
                return HttpResponse(content=f"The raw file could not be converted. Reason: {msg}", status=500)

        # flag tif_exists
        if update_doc or update_tif:
            tmp_cache.flag_tif_exists(foldertype, filename, True)

        tif_filename = copy_filename_as_tif(filename)
        cache_dir = tmp_cache_path(foldertype)
        tif_filepath = os.path.join(cache_dir, tif_filename)

        return self.serve_file(tif_filepath, tif_filename)

    def prov_stats(self, filename):
        entity = filename.replace(".nc", "")
        result = {}

        # Define the tasks to be executed in parallel
        def fetch_count_prov():
            start_time = time.time()
            result = count_prov(entity)
            end_time = time.time()
            logger.debug(f"fetch_count_prov execution time: {end_time - start_time:.2f} seconds")
            return result

        def fetch_source_entities():
            start_time = time.time()
            result = source_entities(entity)
            end_time = time.time()
            logger.debug(f"fetch_source_entities execution time: {end_time - start_time:.2f} seconds")
            return result

        def fetch_result_entities():
            start_time = time.time()
            result = result_entities(entity)
            end_time = time.time()
            logger.debug(f"fetch_result_entities execution time: {end_time - start_time:.2f} seconds")
            return result

        def fetch_activities():
            start_time = time.time()
            result = activities(entity)
            end_time = time.time()
            logger.debug(f"fetch_activities execution time: {end_time - start_time:.2f} seconds")
            return result

        def fetch_base_for_entities():
            start_time = time.time()
            result = base_for_entities(entity)
            end_time = time.time()
            logger.debug(f"fetch_base_for_entities execution time: {end_time - start_time:.2f} seconds")
            return result
        start_time = time.time()
        # Use ThreadPoolExecutor to execute tasks in parallel
        with ThreadPoolExecutor() as executor:
            futures = {
                "count": executor.submit(fetch_count_prov),
                "source_entities": executor.submit(fetch_source_entities),
                "result_entities": executor.submit(fetch_result_entities),
                "activities": executor.submit(fetch_activities),
                "base_for_entities": executor.submit(fetch_base_for_entities),
            }

            # Collect the results
            for key, future in futures.items():
                result[key] = future.result()
        end_time = time.time()
        logger.debug(f"create result object execution time: {end_time - start_time:.2f} seconds")

        return HttpResponse(content=json.dumps(result), content_type="application/json")


@api_view(["GET"])
def test_xclim(request):
    year_end = "1951"

    # reassign the testing.open_dataset(..) call if needed, for now no assignment
    # because of flake errors
    # tasmax =
    testing.open_dataset(
        "/opt/xclim/" + year_end + "/tasmax_" + year_end + "_.nc"
    )

    return Response("sdfsdf", status=200)


@api_view(["GET"])
def get_climate_layers(request):
    try:
        climate_layers = ClimateLayer.objects.all()
    except ClimateLayer.DoesNotExist:
        climate_layers = None

    if climate_layers:
        serializer = ClimateLayerSerializer(climate_layers, many=True)
        return Response(serializer.data, status=200)
    else:
        return HttpResponse(status=204)


@api_view(["GET"])
def get_climate_layer(request):
    try:
        climate_layer = ClimateLayer.objects.get(pk=request.query_params.get("id"))
    except ClimateLayer.DoesNotExist:
        climate_layer = None

    if climate_layer:
        serializer = ClimateLayerSerializer(climate_layer)
        return Response(serializer.data, status=200)
    else:
        return HttpResponse(status=204)


@api_view(["GET"])
def download(request):
    if not request.query_params.get("id"):
        return HttpResponse(status=400, content="ID missing or does not exists")

    try:

        climate_layer = ClimateLayer.objects.get(pk=request.query_params.get("id"))
    except ClimateLayer.DoesNotExist:
        climate_layer = None
        return HttpResponse(status=400, content="ID missing or does not exists")

    if climate_layer:
        filepath = climate_layer.local_path
        if filepath.endswith(".tar"):
            tar_file_path = filepath
            file = climate_layer.file_name
            extract_to = "/opt/rbis/www/tippecc_data/tmp/"
            file_list = [file]

            pattern = "/opt/rbis/www/tippecc_data/**/" + climate_layer.file_name
            for fname in glob.glob(pattern, recursive=True):
                if os.path.isfile(fname):
                    filepath = fname
                    print("File exists: " + filepath)

            # if os.path.exists(extract_to + file):
            #     print("File exists: " + file)
            #     pass
            if os.path.exists(filepath) and not filepath.endswith(".tar"):
                print("File exists: " + filepath)
                pass
            else:
                extract_specific_files(tar_file_path, extract_to, file_list)
                filepath = extract_to + file
        else:
            pass

        print("Text coordinates")
        if (
                request.query_params.get("latmin")
                and request.query_params.get("latmax")
                and request.query_params.get("lonmin")
                and request.query_params.get("lonmax")
        ):
            print("All true")
            extract_to = "/opt/rbis/www/tippecc_data/tmp/"
            latmin = request.query_params.get("latmin")
            latmax = request.query_params.get("latmax")
            lonmin = request.query_params.get("lonmin")
            lonmax = request.query_params.get("lonmax")

            try:
                float(latmin)
                float(latmax)
                float(lonmin)
                float(lonmax)
            except Exception:
                return HttpResponse(status=400, content="coordinates are not a number")

            # Todo: check coordinates within extent

            filename, file_extension = os.path.splitext(filepath.split("/")[-1])
            file_out = (
                    extract_to
                    + "/"
                    + filename
                    + "_tmp_"
                    + str(lonmin)
                    + "%"
                    + str(lonmax)
                    + "%"
                    + str(latmin)
                    + "%"
                    + str(latmax)
                    + file_extension
            )
            print(file_out)
            if os.path.exists(file_out):
                print("File exists: " + file_out)
                pass
            else:
                slice_bbox(filepath, file_out, lonmin, lonmax, latmin, latmax)
            filepath = file_out

        if request.query_params.get("year_start") and request.query_params.get(
                "year_end"
        ):
            begin_year = climate_layer.date_begin.year
            end_year = climate_layer.date_end.year

            year_start = request.query_params.get("year_start")
            year_end = request.query_params.get("year_end")

            if not year_start.isdigit() or not year_end.isdigit():
                return HttpResponse(
                    status=400, content="year_start or year_end id not a year"
                )

            if (
                    int(year_start) <= begin_year
                    or int(year_start) >= end_year
                    or int(year_end) <= begin_year
                    or int(year_end) >= end_year
                    or int(year_end) < int(year_start)
            ):
                return HttpResponse(
                    status=400,
                    content="year_start or year_end outside of possible range",
                )

            filename, file_extension = os.path.splitext(filepath.split("/")[-1])
            file_out = (
                    extract_to
                    + "/"
                    + filename
                    + "_"
                    + year_start
                    + "-"
                    + year_end
                    + file_extension
            )
            if os.path.exists(file_out):
                print("File exists: " + file_out)
                pass
            else:
                slice_time(
                    filepath,
                    file_out,
                    year_start,
                    year_end,
                    str(climate_layer.date_begin.year),
                )
            filepath = file_out

        # type = mimetypes.guess_type(filepath)[0] or mimetypes.guess_type(filepath)[1]
        # file = open(filepath, "rb")
        # response = HttpResponse(file, content_type=type)
        # response["Content-Disposition"] = "attachment; filename= %s" % os.path.basename(
        #     filepath
        # )
        # return response

        url = (
                "https://leutra.geogr.uni-jena.de/tippecc_data/tmp/"
                + filepath.split("/")[-1]
        )
        filename = os.path.basename(url)
        r = requests.get(url, stream=True)
        response = StreamingHttpResponse(streaming_content=r)
        response["Content-Disposition"] = (
                "attachement; filename= %s" % os.path.basename(filepath)
        )
        # return local path instead of URL
        if request.query_params.get("path"):
            if request.query_params.get("path") == "true":
                return HttpResponse(status=200, content=filepath)

        return response
    else:
        return HttpResponse(status=204)


class Elasticsearch(APIView):
    def get(self, request):

        search = dict()
        search["text"] = False
        search["east"] = False
        search["west"] = False
        search["north"] = False
        search["south"] = False
        search["variable_standard_name_cf"] = False
        search["variable_name"] = False
        search["frequency"] = False
        search["scenario"] = False
        search["gcm"] = False
        search["rcm"] = False
        search["bias_correction"] = False
        search["start_year"] = False
        search["end_year"] = False

        search["text"] = request.query_params.get("search_text")
        search["variable_standard_name_cf"] = request.query_params.get(
            "variable_standard_name_cf"
        )
        search["variable_name"] = request.query_params.get("variable_name")
        search["frequency"] = request.query_params.get("frequency")
        search["scenario"] = request.query_params.get("scenario")
        search["gcm"] = request.query_params.get("gcm")
        search["rcm"] = request.query_params.get("rcm")
        search["bias_correction"] = request.query_params.get("bias_correction")
        search["start_year"] = request.query_params.get("start_year")
        search["end_year"] = request.query_params.get("end_year")

        ws = ClimateSearch(search)
        count = ws.count()  # Total count of result)
        response = ws[
                   0:count
                   ].execute()  # default size is 10 -> set size to total count

        # print response.__dict__

        finalJSON = {"hits": [], "facets": []}

        hits = []
        facets = dict()
        list_order = dict()

        # for facet in response.facets:
        #     print facet
        #     for (facet, count, selected) in response.facets[facet]:
        #         print(facet, ' (SELECTED):' if selected else ':', count)

        for hit in response:
            print(hit)
            # topics = []
            # if hasattr(hit, 'topiccat'):
            #     if hit.topiccat:
            #         for topic in hit.topiccat:
            #             topics.append({'val': topic})

            # keywords = []
            # if hasattr(hit, 'keywords'):
            #     print hit.keywords
            #     print hit.meta.id
            #     if hit.keywords:
            #         for keyword in hit.keywords:
            #             keywords.append({'val': keyword})
            if hit.meta.index == "climate_index":
                hits.append(
                    {
                        "score": round(hit.meta.score, 3),
                        "title": hit.title,
                        "django_id": hit.meta.id,
                        "description": hit.description,
                        "path": hit.link,
                        "dataset": hit.dataset,
                    }
                )

        list_order["title"] = 11
        list_order["variable_standard_name_cf"] = 12
        list_order["gcm"] = 13
        list_order["rcm"] = 14
        list_order["variable_name"] = 15
        list_order["frequency"] = 16
        list_order["scenario"] = 17
        list_order["bias_correction"] = 18
        list_order["start_year"] = 19
        list_order["end_year"] = 20
        list_order["variable_abbr"] = 21

        facets_ordered = []

        for facet in response.facets:
            for facet_, count, selected in response.facets[facet]:
                if len(facet_) > 0:
                    if facet not in facets:
                        facets[facet] = []
                        facets[facet] = [{"name": facet_, "count": count}]
                        facets_ordered.append(
                            {"name": facet, "order": list_order[facet]}
                        )
                    else:
                        facets[facet].append({"name": facet_, "count": count})

        finalJSON["hits"] = hits
        finalJSON["facets"] = facets
        finalJSON["facets_ordered"] = facets_ordered

        return Response(finalJSON)


class GenerateDatView(APIView):
    def get(self, request):
        """
        Starts a long-running process to calculate the dat file for a nc-file
        """
        foldertype = parse_temp_foldertype_from_param(request.GET.get("type", default=None))
        filename = parse_temp_filename_from_param(request.GET.get("name", default=None), foldertype)
        try:
            # Start the long-running process in a separate thread
            process_thread = threading.Thread(target=extract_jams_files, args=(foldertype, filename))
            process_thread.start()

            # Wait for the thread to complete
            process_thread.join()

            # Return a 200 response to indicate the process was successfully completed
            return JsonResponse({"message": "Process completed successfully"}, status=200)
        except Exception as e:
            # If there was an error starting the process, log the exception
            print(f"Error starting process: {e}")
            # Return a 500 response to indicate an internal server error
            return JsonResponse({"error": "Failed to start process"}, status=500)
        # finally:
        #     # TODO: - check if this is correct or needs to be moved
        #     # use this to set the existence of the dat file in cache
        #     tmp_cache.flag_dat_exists(foldertype, filename, True)


class ElasticsearchCollections(APIView):
    def get(self, request):

        search = dict()
        search["text"] = False
        search["east"] = False
        search["west"] = False
        search["north"] = False
        search["south"] = False
        search["variable_abbr"] = False
        search["frequency"] = False
        search["scenario"] = False
        search["gcm"] = False
        search["rcm"] = False
        search["bias_correction"] = False
        search["start_year"] = False
        search["end_year"] = False

        search["text"] = request.query_params.get("search_text")
        search["variable_abbr"] = request.query_params.get("variable_abbr")
        search["frequency"] = request.query_params.get("frequency")
        search["scenario"] = request.query_params.get("scenario")
        search["gcm"] = request.query_params.get("gcm")
        search["rcm"] = request.query_params.get("rcm")
        search["bias_correction"] = request.query_params.get("bias_correction")
        search["start_year"] = request.query_params.get("start_year")
        search["end_year"] = request.query_params.get("end_year")
        search["processing_method"] = request.query_params.get("processing_method")

        ws = ClimateCollectionSearch(search)
        count = ws.count()  # Total count of result)
        response = ws[
                   0:count
                   ].execute()  # default size is 10 -> set size to total count

        # print response.__dict__

        finalJSON = {"hits": [], "facets": []}

        hits = []
        facets = dict()
        list_order = dict()

        # for facet in response.facets:
        #     print facet
        #     for (facet, count, selected) in response.facets[facet]:
        #         print(facet, ' (SELECTED):' if selected else ':', count)

        for hit in response:
            print(hit.to_dict())

            variables = []
            if hasattr(hit, "variables"):
                if hit.variables:
                    for variable in hit.variables:
                        variables.append({"val": variable})

            # keywords = []
            # if hasattr(hit, 'keywords'):
            #     print hit.keywords
            #     print hit.meta.id
            #     if hit.keywords:
            #         for keyword in hit.keywords:
            #             keywords.append({'val': keyword})
            if hit.meta.index == "climate_collection_index":
                hits.append(
                    {
                        "score": round(hit.meta.score, 3),
                        "scenario": hit.scenario,
                        "gcm": hit.gcm,
                        "rcm": hit.rcm,
                        "processing_method": hit.processing_method,
                    }
                )

        list_order["title"] = 11
        list_order["variables"] = 12
        list_order["gcm"] = 13
        list_order["rcm"] = 14
        list_order["variable_name"] = 15
        list_order["frequency"] = 16
        list_order["scenario"] = 17
        list_order["processing_method"] = 18
        list_order["start_year"] = 19
        list_order["end_year"] = 20
        list_order["variable_abbr"] = 21
        list_order["file_id"] = 22

        facets_ordered = []

        for facet in response.facets:
            for facet_, count, selected in response.facets[facet]:
                if len(facet_) > 0:
                    if facet not in facets:
                        facets[facet] = []
                        facets[facet] = [{"name": facet_, "count": count}]
                        facets_ordered.append(
                            {"name": facet, "order": list_order[facet]}
                        )
                    else:
                        facets[facet].append({"name": facet_, "count": count})

        finalJSON["hits"] = hits
        finalJSON["facets"] = facets
        finalJSON["facets_ordered"] = facets_ordered

        return Response(finalJSON)


def extract_specific_files(tar_file_path, extract_to, file_list):
    with tarfile.open(tar_file_path, "r") as tar:
        tar.getmembers()
        for file_name in file_list:
            for member in tar.getmembers():
                if file_name in str(member):
                    print(member)
                    try:
                        member.name = os.path.basename(member.name)
                        tar.extract(member, path=extract_to)
                        # os.chown(extract_to + file_name, uid, gid)
                        # until uid and gid are defined, they are replaced with None
                        os.chown(extract_to + file_name, None, None)
                    except KeyError:
                        print(
                            f"Warning: File '{file_name}' not found in the tar archive."
                        )


class ElasticsearchIndicators(APIView):
    def get(self, request):

        search = dict()
        search["text"] = False
        search["east"] = False
        search["west"] = False
        search["north"] = False
        search["south"] = False
        search["variable_abbr"] = False
        search["frequency"] = False
        search["scenario"] = False
        search["gcm"] = False
        search["rcm"] = False
        search["bias_correction"] = False
        search["year_begin"] = False
        search["year_end"] = False
        search["indicator"] = False
        search["periode"] = False
        search["title"] = False
        search["dataset"] = False

        search["text"] = request.query_params.get("search_text")
        search["variable_abbr"] = request.query_params.get("variable_abbr")
        search["frequency"] = request.query_params.get("frequency")
        search["scenario"] = request.query_params.get("scenario")
        search["gcm"] = request.query_params.get("gcm")
        search["rcm"] = request.query_params.get("rcm")
        search["bias_correction"] = request.query_params.get("bias_correction")
        search["year_begin"] = request.query_params.get("year_begin")
        search["year_end"] = request.query_params.get("year_end")
        search["indicator"] = request.query_params.get("indicator")
        search["periode"] = request.query_params.get("periode")
        search["dataset"] = request.query_params.get("dataset")

        ws = ClimateIndicatorSearch(search)
        count = ws.count()  # Total count of result)
        response = ws[0].execute()  # default size is 10 -> set size to total count

        # print response.__dict__

        finalJSON = {"hits": [], "facets": []}

        hits = []
        facets = dict()
        list_order = dict()

        for hit in response:
            print(hit.to_dict())

            if hit.meta.index == "climate_indicator_index":
                hits.append({"score": round(hit.meta.score, 3), "title": hit.rcm})

        list_order["indicator"] = 12
        list_order["gcm"] = 13
        list_order["rcm"] = 14
        list_order["variable_name"] = 15
        list_order["periode"] = 16
        list_order["scenario"] = 17
        list_order["indicator"] = 18
        list_order["variable_abbr"] = 21
        list_order["file_id"] = 22
        list_order["year_begin"] = 23
        list_order["year_end"] = 24
        list_order["title"] = 110
        list_order["dataset"] = 110

        facets_ordered = []

        for facet in response.facets:
            for facet_, count, selected in response.facets[facet]:
                if len(facet_) > 0:
                    if facet not in facets:
                        facets[facet] = []
                        facets[facet] = [{"name": facet_, "count": count}]
                        facets_ordered.append(
                            {"name": facet, "order": list_order[facet]}
                        )
                    else:
                        facets[facet].append({"name": facet_, "count": count})

        finalJSON["hits"] = hits
        finalJSON["facets"] = facets
        finalJSON["facets_ordered"] = facets_ordered

        return Response(finalJSON)


def slice_bbox(file, file_out, lonmin, lonmax, latmin, latmax):
    # cdo=Cdo()
    # cdo.sellonlatbox(lonmin,lonmax,latmin,latmax,input=file,output=file_out,options="-f nc4")
    import subprocess

    path_python = sys.executable
    path_script = os.path.dirname(__file__)
    try:
        subprocess.run(
            [
                path_python,
                path_script + "/cdo_calls.py",
                "bbox",
                file,
                file_out,
                lonmin,
                lonmax,
                latmin,
                latmax,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Command {e.cmd} failed with error {e.returncode}")


def slice_time(file, file_out, year_from, year_to, ref_start):
    # cdo=Cdo()
    # cdo.seltimestep(1,360, input=file,output=file_out,options="-f nc4")
    import subprocess

    path_python = sys.executable
    path_script = os.path.dirname(__file__)
    try:
        subprocess.run(
            [
                path_python,
                path_script + "/cdo_calls.py",
                "time",
                file,
                file_out,
                year_from,
                year_to,
                ref_start,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Command {e.cmd} failed with error {e.returncode}")


def bulk_indexing():
    from .models import (ClimateLayer, ClimateModelling,)

    # connections.create_connection(hosts='http://localhost:9200', timeout=20)
    connections.create_connection(
        hosts="https://leutra.geogr.uni-jena.de:443/es1453d", timeout=20
    )
    climate_index = Index("climate_index")
    climate_index.delete(ignore=404)
    ClimateDatasetsIndex.init()
    [b.indexing() for b in ClimateLayer.objects.all().iterator()]

    climate_collections_index = Index("climate_collection_index")
    climate_collections_index.delete(ignore=404)
    ClimateDatasetsCollectionIndex.init()
    climateDatasetCollections = ClimateModelling.objects.all()
    for climateDatasetCollection in climateDatasetCollections:
        files = ClimateLayer.objects.filter(dataset=climateDatasetCollection.id)
        variables = []
        processing_method = None
        for file in files:
            variables.append(
                {
                    "variable_abbr": file.variable.variable_abbr,
                    "file_id": file.variable.variable_abbr + "_" + str(climateDatasetCollection.id) + "_" + str(file.id),
                    "frequency": file.frequency,
                    "start_year": file.date_begin,
                    "date_begin": file.date_end,
                }
            )
            if file.processing_method:
                processing_method = str(file.processing_method.name)
        if len(variables) > 0:
            obj = ClimateDatasetsCollectionIndex(
                rcm=str(climateDatasetCollection.modellingBase.regional_model),
                gcm=str(climateDatasetCollection.modellingBase.forcing_global_model),
                scenario=str(climateDatasetCollection.scenario),
                processing_method=str(processing_method),
                variables=variables,
            )
            print(obj)
            obj.save()


def read_and_insert_ind_index_data(myPath, dataset_):
    connections.create_connection(
        hosts="https://leutra.geogr.uni-jena.de:443/es1453d", timeout=20
    )
    # climate_index = Index('climate_indicator_index')
    # climate_index.delete(ignore=404)
    ClimateIndicatorIndex.init()

    filesList = []

    for path, subdirs, files in os.walk(myPath):
        for name in files:
            filesList.append(os.path.join(path, name))

    theDict = dict()
    for something in filesList:  # Calculate size for all files here.
        theStats = os.stat(something)
        theDict[something] = theStats

    for item in theDict:
        print(
            item.replace("/opt/rbis/www/", "http://leutra.geogr.uni-jena.de/"),
            round(theDict[item].st_size / (pow(1024, 2)), 2),
            "MB",
        )
        if item.endswith("nc"):
            # tar = tarfile.open(item)
            # tar.getmembers()
            # for member in tar.getmembers():
            #    print(member)
            a = 0
            title = item.split("/")[-1]
            if "_rcp" in item:
                a = 0
                scenario = title.split("_")[-1].split(".")[0]
            else:
                a = 1
                scenario = ""
            #     path = item

            print(title)
            gcm = title.split("_")[(-2 + a)].split(".")[0]

            print(title.split("_")[-4 + a])
            if "-" in title.split("_")[-4 + a]:
                rcm = title.split("_")[-3 + a]
                start = title.split("_")[(-4 + a)].split("-")[0]
                end = title.split("_")[(-4 + a)].split("-")[1]

            else:
                rcm = ""
                start = title.split("_")[(-3 + a)].split("-")[0]
                end = title.split("_")[(-3 + a)].split("-")[1]
            indicator = title.split("-")[0].replace("tippecc_", "")[:-5]

            obj = ClimateIndicatorIndex(
                rcm=str(rcm),
                gcm=str(gcm),
                scenario=scenario,
                indicator=indicator,
                title=title,
                year_begin=str(start),
                year_end=str(end),
                periode=start + "-" + end,
                dataset=dataset_,
            )
            print(obj)
            obj.save()


def read_and_insert_ind_index_slice_data(myPath, dataset_):
    connections.create_connection(
        hosts="https://leutra.geogr.uni-jena.de:443/es1453d", timeout=20
    )

    # climate_index = Index("climate_indicator_index")
    # climate_index.delete(ignore=404)
    # ClimateIndicatorIndex.init()

    filesList = []

    for path, subdirs, files in os.walk(myPath):
        for name in files:
            filesList.append(os.path.join(path, name))

    theDict = dict()
    for something in filesList:  # Calculate size for all files here.
        theStats = os.stat(something)
        theDict[something] = theStats

    for item in theDict:
        print(
            item.replace("/opt/rbis/www/", "http://leutra.geogr.uni-jena.de/"),
            round(theDict[item].st_size / (pow(1024, 2)), 2),
            "MB",
        )
        if item.endswith("nc"):
            # tar = tarfile.open(item)
            # tar.getmembers()
            # for member in tar.getmembers():
            #    print(member)
            a = 0
            title = item.split("/")[-1]
            if "_rcp" in item:
                a = 0
                scenario = title.split("_")[-1].split(".")[0]
            else:
                a = 1
                scenario = ""
            #     path = item

            print(title)
            gcm = title.split("_")[(-2 + a)].split(".")[0]

            print(title.split("_")[-4 + a])
            if "-" in title.split("_")[-4 + a]:
                rcm = title.split("_")[-3 + a]
                # start = title.split("_")[(-4 + a)].split("-")[0]
                # end = title.split("_")[(-4 + a)].split("-")[1]

            else:
                rcm = ""
                # start = title.split("_")[(-3 + a)].split("-")[0]
                # end = title.split("_")[(-3 + a)].split("-")[1]

            start = title.split("_")[1].split("-")[0]
            end = title.split("_")[1].split("-")[1]
            indicator = title.split("-")[1].replace("tippecc_", "")[5:-5]

            obj = ClimateIndicatorIndex(
                rcm=str(rcm),
                gcm=str(gcm),
                scenario=scenario,
                indicator=indicator,
                title=title,
                year_begin=str(start),
                year_end=str(end),
                periode=start + "-" + end,
                dataset=dataset_,
            )
            print(obj)
            obj.save()


# connections.create_connection(hosts='https://leutra.geogr.uni-jena.de:443/es1453d', timeout=20)
# climate_index = Index('climate_indicator_index')
# climate_index.delete(ignore=404)
# read_and_insert_ind_index_data("/opt/rbis/www/tippecc_data/LANDSURF_indictor/full_period", "monthly")
# read_and_insert_ind_index_slice_data("/opt/rbis/www/tippecc_data/LANDSURF_indictor/slices20", "mean 20 years")
# read_and_insert_ind_index_slice_data("/opt/rbis/www/tippecc_data/LANDSURF_indictor/slices30", "mean 30 years")
# bulk_indexing()


def delete_all_temp_results():
    """Deletes all database TempResultFiles objects. Use with care."""
    TempResultFile.objects.all().delete()


def init_temp_results_folders():
    created_objs_counter = 0

    for foldertype in TEMP_FOLDER_TYPES:
        print(f"Initiating TempResultFiles folder with category: {foldertype}")
        folder_root_path = tmp_raw_path(foldertype)

        # TODO: - maybe here, add automic directory routine based on settings
        # currently if the path does not exist, just continue
        if not folder_root_path:
            continue

        filenames = os.listdir(folder_root_path)
        for filename in filenames:
            extract_ncfile(filename, foldertype)
    # post creation handling (?)
    print(f"Finished TempResultFiles Init. Created {created_objs_counter} database objects.")


def helper_update_nodatavalue():
    for temp_file in TempResultFile.objects.all():
        filepath = tmp_raw_filepath(temp_file.category, temp_file.filename)
        if not filepath:
            continue
        if in_sizelimit_conversion(filepath):
            new_nc_meta = helper_read_and_add_nodatavalue(temp_file.nc_meta, filepath)
            temp_file.nc_meta = new_nc_meta
            temp_file.save()
        else:
            continue


# helper_update_nodatavalue()

# def update_all_tempfolders():
#     for foldertype in TEMP_FOLDER_TYPES:
#         tmp_cache.update_by_foldertype(foldertype)


# delete_all_temp_results()
# init_temp_results_folders()
# update_all_tempfolders()
