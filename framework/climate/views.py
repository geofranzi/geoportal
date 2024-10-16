import glob
# import grp
import json
# import mimetypes
import os
# import pwd
import sys
# import xarray as xr
# import cf_xarray as cfxr
import tarfile
import uuid
from datetime import datetime
from pathlib import Path
from subprocess import (PIPE, Popen,)

import requests
# from django.conf import settings
from django.http import (HttpResponse, JsonResponse, StreamingHttpResponse,)
from elasticsearch_dsl import Index
from elasticsearch_dsl.connections import connections
from osgeo import gdal
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
# import xclim.indices
from xclim import testing

from .models import (ClimateLayer, TempResultFile,)
from .search_es import (ClimateCollectionSearch, ClimateDatasetsCollectionIndex, ClimateDatasetsIndex,
                        ClimateIndicatorIndex, ClimateIndicatorSearch, ClimateSearch,)
from .serializer import ClimateLayerSerializer


# GENERAL_API_URL = "http://127.0.0.1:8000/"
GENERAL_API_URL = "https://leutra.geogr.uni-jena.de/backend_geoportal/"

HASH_LENGTH = 32  # custom length for temporary .txt files generated during wget request
TEMP_FILESIZE_LIMIT = 75  # filesize limit in MB for conversion (nc -> tif)
TEMP_NUM_BANDS_LIMIT = 1300  # bands limit as number for conversion (nc -> tif)


TEMP_FOLDER_TYPES = [
    "water_budget",
    "water_budget_bias",
    "kariba",
    "vaal",
    "cmip6",
    "paper",
    "luanginga",
    "ind_full",
    "ind_slices20",
    "ind_slices30"
]

folder_list = {}
folder_list['raw'] = {}
folder_list['cache'] = {}

tempfolders_content = {}

# LOCAL paths
# TEMP_ROOT = settings.STATICFILES_DIRS[0]
# TEMP_RAW = os.path.join(TEMP_ROOT, "tippecctmp/raw")
# TEMP_CACHE = os.path.join(TEMP_ROOT, "tippecctmp/cache")
# TEMP_URL = os.path.join(TEMP_ROOT, "tippecctmp/url")
# URLTXTFILES_DIR = TEMP_URL

# SERVER paths
TEMP_ROOT = "/data/tmp"
TEMP_RAW = "/data"
TEMP_CACHE = "/data/tmp/cache"
URLTXTFILES_DIR = "/data/tmp/url"

for TEMP_FOLDER_TYPE in TEMP_FOLDER_TYPES:
    folder_list['raw'][TEMP_FOLDER_TYPE] = os.path.join(TEMP_RAW, TEMP_FOLDER_TYPE)
    folder_list['cache'][TEMP_FOLDER_TYPE] = os.path.join(TEMP_CACHE, TEMP_FOLDER_TYPE)
    tempfolders_content[TEMP_FOLDER_TYPE] = {}

    # print("FOLDER_LIST")
    # print(folder_list)

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


def parse_temp_foldertype_from_param(foldertype: str):
    """Checks if a foldertype exists as a key in TEMP_FOLDER_TYPES.
    :return: foldertype or false if not exists.
    """
    try:
        idx = TEMP_FOLDER_TYPES.index(foldertype)
        return TEMP_FOLDER_TYPES[idx]
    except Exception:
        return False


# Safely returns an actual filename from the raw directory of temp result files
# based on given foldertype and filename string - request parameters.
# TODO: - add function to parse as list
def parse_temp_filename_from_param(filename: str, foldertype: str):
    """Checks if a filename exists in a specific foldertype folder.
    :return: filename or false if not exists.
    """
    foldertype = parse_temp_foldertype_from_param(foldertype)
    if foldertype is False:
        return False

    try:
        folder = os.listdir(folder_list['raw'][foldertype])
        idx = folder.index(filename)
        return folder[idx]
    except Exception:
        return False


def parse_urltxt_filename_from_param(hash: str):
    """Checks if a hash-string exists as a filename in URLTXTFILES_DIR.
    :return: filename or false if not exists.
    """
    filename = f"{hash}.txt"
    try:
        folder = os.listdir(URLTXTFILES_DIR)
        idx = folder.index(filename)
        return folder[idx]
    except Exception:
        return False


def check_temp_result_filesize(filepath: str):
    size = (os.stat(filepath).st_size / 1024) / 1024  # MB
    if size > TEMP_FILESIZE_LIMIT:
        return False
    else:
        return True


def check_temp_result_filesize_from_st_size(st_size):
    size = (st_size / 1024) / 1024  # MB
    if size > TEMP_FILESIZE_LIMIT:
        return False
    else:
        return True


def temp_cat_filename(category: str, filename: str):
    return os.path.join(category, filename)


def copy_filename_as_tif(f: str):
    return f"{Path(f).stem}.tif"


def cache_tif_from_nc(filename_in: str, foldertype: str, temp_doc: TempResultFile) -> tuple[bool, str]:
    """Tries to create a tif from a nc file in a specific folder.
    Tif will be written to folder_list['cache'][foldertype].
    :param filename_in: nc filename (input file)
    :param foldertype: foldertype from TEMP_FOLDER_TYPES
    :param temp_doc: TempResultFile object of the input file

    :return: tuple[bool, str] ... ([success, contextmessage])
    """
    filepath_in = os.path.join(folder_list['raw'][foldertype], filename_in)
    if not os.path.isfile(filepath_in):
        return False, "No raw file"

    if not check_temp_result_filesize(filepath_in):
        return False, "Raw file too big"

    if temp_doc.num_bands is None:
        return False, "Could not convert to tif because of missing metadata"

    if not is_temp_file_tif_convertable(filename_in, foldertype, temp_doc):
        return False, "Raw file not tif convertable"

    filename_out = copy_filename_as_tif(filename_in)
    filepath_out = os.path.join(folder_list['cache'][foldertype], filename_out)

    # print(f"filename_out: {filename_out}")
    # print(f"filepath_in: {filepath_in}")
    # print(f"filepath_out: {filepath_out}")

    # Set destination spatial reference
    kwargs = {"dstSRS": 'EPSG:4326'}

    try:
        # for some reason, tif files created via translate are
        # not allways working correctly in our visualization
        gdal.Warp(filepath_out, filepath_in, **kwargs)
        fileversion_out = os.stat(filepath_out).st_mtime
        temp_doc.st_mtime_tif = fileversion_out
        temp_doc.save()
        return True, ""
    except Exception as e:
        print(e)
        return False, "Conversion failed"


def is_temp_file_cached(raw_filename: str, foldertype: str, temp_doc: TempResultFile) -> bool:
    """Checks if a up-to-date tif file exists for a corresponding nc file.
    """
    tif_filename = copy_filename_as_tif(raw_filename)
    tif_path = os.path.join(folder_list['cache'][foldertype], tif_filename)

    if not os.path.isfile(tif_path):
        return False

    tif_version = os.stat(tif_path).st_mtime
    if not temp_doc.check_cache_version(tif_version):
        return False

    # file exists, and version matches
    return True


def is_temp_file_tif_convertable(raw_filename: str, foldertype: str, temp_doc: TempResultFile) -> bool:
    """Checks if our custom constraints for (nc -> tif) file conversion are met. It might still
    happen that conversion fails (e.g. we have no metadata yet and only assume it's possible).
    """
    filepath = os.path.join(folder_list['raw'][foldertype], raw_filename)
    if not check_temp_result_filesize(filepath):
        return False

    if temp_doc.num_bands is None:
        return True
    elif temp_doc.num_bands <= TEMP_NUM_BANDS_LIMIT:
        return True
    else:
        return False


def extract_ncfile_lite(filename: str, source_dir: str, file_category: str, force_update=False):
    """Read filesize and creation time from a file and create/update the specific TempResultFile.

    :return: tuple[bool, str|TempResultFile]
             on success [true, TempResultFile]
             on failure [false, str]
    """
    cat_filename = temp_cat_filename(file_category, filename)
    filepath = os.path.join(source_dir, filename)
    if not os.path.isfile(filepath):
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
            category=file_category
        )
        new_doc.save()
    except Exception as e:
        print(e)
        return False, "could not save file metadata to database"

    return True, new_doc


def extract_ncfile_metadata(filename: str, source_dir: str, file_category: str, force_update=False):
    """Tries to read all metadata necessary to us from a nc file and create/update the specific TempResultFile.

    :return: tuple[bool, str|TempResultFile]
            on success [true, TempResultFile]
            on failure [false, str]
    """
    # filename with category prefix, unique over all TempResultFiles
    cat_filename = temp_cat_filename(file_category, filename)

    filepath = os.path.join(source_dir, filename)
    if not os.path.isfile(filepath):
        return False, "file not found"

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
            if not old_doc.check_raw_version(st_mtime_nc) or force_update:
                old_doc.delete()
    except Exception:
        pass

    JSON_metadata = None
    try:
        # reading metadata via gdalinfo script
        process = Popen(["gdalinfo", filepath, "-json", "-mm"], stdout=PIPE, stderr=PIPE)
        # process = Popen(f"gdalinfo data/tif_data/{input_filename} -json")
        stdout, stderr = process.communicate()
        metadata = stdout.decode("utf-8")

        JSON_metadata = json.loads(metadata)
    except Exception as e:
        print(e)
        return False, "gdalinfo could not process file correctly"

    # checking and parsing needed metadata values
    if "bands" not in JSON_metadata:
        return False, "band metadata missing in file"

    num_bands = len(JSON_metadata["bands"])

    net_cdf_times = None
    try:
        net_cdf: str = JSON_metadata["metadata"][""]["NETCDF_DIM_time_VALUES"]
        net_cdf = net_cdf.replace("{", "").replace("}", "").replace(" ", "")
        net_cdf_times = json.dumps(net_cdf.split(","))
    except Exception:
        return False, "netcdf times missing in file"

    timestamp_begin = ""
    try:
        timestamp_begin: str = JSON_metadata["metadata"][""]["time#units"]
        timestamp_begin = timestamp_begin.split(' ')[-1]
    except Exception:
        timestamp_begin = ""

    # assembling metadata values
    complete_band_metadata = {}

    try:
        for i, band_metadata in enumerate(JSON_metadata["bands"]):
            band_collect = {}
            band_collect["min"] = band_metadata["computedMin"]
            band_collect["max"] = band_metadata["computedMax"]
            band_collect["NETCDF_DIM_time"] = band_metadata["metadata"][""][
                "NETCDF_DIM_time"
            ]
            band_collect["index"] = i + 1
            complete_band_metadata[str(i + 1)] = band_collect
    except Exception:
        return False, "missing metadata key,value pairs"

    new_doc = None
    try:
        # print("Attempting file metadata save: ")
        # print(
        #     f"filepath: {filepath}\nnum_bands:{num_bands}\nnet_cdf_times:{net_cdf_times}"
        # )
        new_doc = TempResultFile(
            categorized_filename=cat_filename,
            filename=filename,
            num_bands=num_bands,
            band_metadata=complete_band_metadata,
            net_cdf_times=net_cdf_times,
            st_mtime_nc=st_mtime_nc,
            st_size_nc=st_size_nc,
            category=file_category,
            timestamp_begin=timestamp_begin
        )
        new_doc.save()
    except Exception as e:
        print(e)
        return False, "could not save file metadata to database"

    return True, new_doc


def read_folder_constrained(source_dir: str, only_nc: bool = False):
    if only_nc:
        # reads only files ending with .nc from source_dir
        foldercontent = list((file for file in os.listdir(source_dir)
                             if (os.path.isfile(os.path.join(source_dir, file)) and Path(file).suffix == '.nc')))
    else:
        # ready all files from source_dir
        foldercontent = list((file for file in os.listdir(source_dir)
                             if (os.path.isfile(os.path.join(source_dir, file)))))

    return foldercontent


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

    filepath = os.path.join(folder_list['raw'][foldertype], filename)
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
        succ, msg = extract_ncfile_metadata(filename, folder_list['raw'][foldertype], foldertype, force_update=True)
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
    if not is_temp_file_cached(filename, foldertype, temp_doc):
        update_tif = True

    if update_tif:
        succ, msg = cache_tif_from_nc(filename, foldertype, temp_doc)
        if not succ:
            # The raw file could not be converted
            # print(f"The raw file could not be converted. Reason: {msg}")
            return HttpResponse(content=f"The raw file could not be converted. Reason: {msg}", status=500)

    # update file in tempfolders_content
    if update_doc or update_tif:
        update_tempfolder_file(foldertype, filename)

    tif_filename = copy_filename_as_tif(filename)
    # cache_dir = folder_list['cache'][foldertype]
    # tif_filepath = os.path.join(cache_dir, tif_filename)

    data = {
        'filename': tif_filename,

        # hardcoded for now, because i'm not absolutely sure on the format
        # TODO: - replace domain and path with variable
        # 'route': f"http://127.0.0.1:8000/static/tippecctmp/cache/{foldertype}/{tif_filename}"
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

    source_dir = folder_list['raw'][foldertype]
    filepath_in = os.path.join(folder_list['raw'][foldertype], filename)
    fileversion = os.stat(filepath_in).st_mtime

    if not os.path.isfile(filepath_in):
        return HttpResponse(content="File does not exist", status=500)

    cat_filename = temp_cat_filename(foldertype, filename)
    temp_doc: TempResultFile = TempResultFile.get_by_cat_filename(cat_filename)

    if not check_temp_result_filesize(filepath_in):
        return HttpResponse(content="File too big to extract metadata", status=500)

    # file does not exist in database
    if temp_doc is None:
        succ, msg = extract_ncfile_metadata(filename, source_dir, foldertype)
        if succ:
            # update file in tempfolders_content
            update_tempfolder_file(foldertype, filename)

            new_doc: TempResultFile = msg
            return JsonResponse({'metadata': new_doc.get_file_metadata()})
        else:
            return HttpResponse(content="Could not extraxt metadata from file.", status=500)

    # version check
    if not temp_doc.check_raw_version(fileversion):
        succ, msg = extract_ncfile_metadata(filename, source_dir, foldertype)
        if succ:
            # update file in tempfolders_content
            update_tempfolder_file(foldertype, filename)

            new_doc: TempResultFile = msg
            return JsonResponse({'metadata': new_doc.get_file_metadata()})
        else:
            return HttpResponse(content="Could not extraxt metadata from file.", status=500)

    # TODO:
    # it can still happen, that there is a file within the size limit, which
    # we have a up to date database object associated, but not yet read the
    # metadata. (fields are Null in that case)
    # - decide on a handling here

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

    if not os.path.isdir(folder_list['raw'][foldertype]):
        return HttpResponse(content="Selected folder does currently not exist and cant be accessed.", status=500)

    foldercontent = os.listdir(folder_list['raw'][foldertype])

    # print(foldercontent)

    url_content = ""
    # for all requested files in requestbody, check if they really exist
    for requested_file in body:
        filename = None
        try:
            idx = foldercontent.index(requested_file[0])
            filetype = requested_file[1]
            filename = foldercontent[idx]
            if filetype != 'tif':
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


def update_tempfolder_file(foldertype, filename):
    """Update one file from a folder given by foldertype, in tempfolders_content.
    - this is not absolutely needed and experimental for now
    - do only use for single file update handling and not in a loop
    - for multiple files just update the whole folder with update_tempfolder_by_type
    """
    source_dir = folder_list['raw'][foldertype]
    cat_filename = temp_cat_filename(foldertype, filename)
    temp_doc: TempResultFile = TempResultFile.get_by_cat_filename(cat_filename)

    filemeta_content = {}
    fileinfo = {}

    # check db fileinfo
    if temp_doc is not None:
        fileinfo['num_bands'] = temp_doc.num_bands

        # tif file state
        tif_cached = is_temp_file_cached(filename, foldertype, temp_doc)
        fileinfo['tif_cached'] = tif_cached

        # tif convertability
        if not tif_cached:
            conv_constraint = is_temp_file_tif_convertable(filename, foldertype, temp_doc)
            fileinfo['tif_convertable'] = conv_constraint
        else:
            fileinfo['tif_convertable'] = True

        fileinfo['fileversion'] = temp_doc.st_mtime_nc
    else:
        fileinfo = None

    try:
        full_filename = os.path.join(source_dir, filename)
        file_stats = os.stat(full_filename)
        creation_date = None
        creation_date = datetime.fromtimestamp(file_stats.st_mtime).strftime(
            "%Y-%m-%d %H:%M"
        )

        filemeta_content['filename'] = filename
        filemeta_content['filesize'] = sizeof_fmt(file_stats.st_size)
        filemeta_content['creation_date'] = creation_date

        # manual version check file <> database
        if fileinfo is not None:
            if fileinfo['fileversion'] != str(file_stats.st_mtime):
                fileinfo = None
            else:
                # manual filesize check
                fileinfo['in_size_limit'] = check_temp_result_filesize_from_st_size(file_stats.st_size)

        # now either None (no database info) or fileinfo
        filemeta_content['fileinfo'] = fileinfo
        filemeta_content['filesuffix'] = Path(filename).suffix

        # NOTE
        #   - update file in tempfolders_content
        #   - this should be secured a little bit better
        tempfolders_content[foldertype][filename] = filemeta_content
    except Exception as e:
        e = e
        print("Fileread ERR, fileupdate failed:\n", e)


def update_tempfolder_by_type(foldertype):
    """Update all files from a folder given by foldertype, in tempfolders_content.
    """
    source_dir = folder_list['raw'][foldertype]

    try:
        foldercontent = read_folder_constrained(source_dir)
    except Exception as e:
        print(e)
        return HttpResponse(content="Reading the content of the selected folder has failed.", status=500)

    # used to collect data on each file
    folder_info = dict.fromkeys(foldercontent, None)

    # helper for the database filter
    cat_helper = []
    for f in foldercontent:
        cat_helper.append(temp_cat_filename(foldertype, f))

    # filter and read fileinfo from database (if available)
    for f_res in TempResultFile.objects.filter(categorized_filename__in=cat_helper):
        if f_res.filename in folder_info:
            folder_info[f_res.filename] = {}
            folder_info[f_res.filename]['num_bands'] = f_res.num_bands

            # tif file state
            tif_cached = is_temp_file_cached(f_res.filename, foldertype, f_res)
            folder_info[f_res.filename]['tif_cached'] = tif_cached

            # convertability
            if not tif_cached:
                conv_constraint = is_temp_file_tif_convertable(f_res.filename, foldertype, f_res)
                folder_info[f_res.filename]['tif_convertable'] = conv_constraint
            else:
                folder_info[f_res.filename]['tif_convertable'] = True

            folder_info[f_res.filename]['fileversion'] = f_res.st_mtime_nc

    # whole folder with fileinfo on each file (from db)
    dir_content = {}

    # now for all files collect and assemble:
    #   - name, size, creation_date, st_mtime, suffix and fileinfo|None
    for i, f in enumerate(foldercontent):
        try:
            full_filename = os.path.join(source_dir, f)
            file_stats = os.stat(full_filename)
            creation_date = None
            creation_date = datetime.fromtimestamp(file_stats.st_mtime).strftime(
                "%Y-%m-%d %H:%M"
            )

            dir_content_element = {}
            dir_content_element['filename'] = f
            dir_content_element['filesize'] = sizeof_fmt(file_stats.st_size)
            dir_content_element['creation_date'] = creation_date

            file_info = folder_info[f]
            # manual version check file <> database
            if file_info is not None:
                if file_info['fileversion'] != str(file_stats.st_mtime):
                    file_info = None
                else:
                    # manual filesize check
                    file_info['in_size_limit'] = check_temp_result_filesize_from_st_size(file_stats.st_size)

            # now either None (no database info) or file_info
            dir_content_element['fileinfo'] = file_info
            dir_content_element['filesuffix'] = Path(f).suffix

            dir_content[f] = dir_content_element
        except Exception as e:
            # file could not be read (this should only ever happen when
            # serverfiles and folder_content go out of sync)
            print("Fileread ERR while processing FolderContent request:\n", e)
            continue

    # update value in tempfolders_content
    tempfolders_content[foldertype] = dir_content


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
        """
        foldertype = parse_temp_foldertype_from_param(request.GET.get("type", default=None))
        if not foldertype:
            return HttpResponse(content="Invalid foldertype", status=400)

        only_convertable = request.GET.get("convertable", default=None)
        if only_convertable is None:
            only_convertable = False
        else:
            only_convertable = True

        if only_convertable:
            response = self.retrieve_content_only_convertable(foldertype)
            return response
        else:
            response = self.retrieve_content_all(foldertype)
            return response

    def retrieve_content_all(self, foldertype):
        """All files from folder.
        """
        source_dir = folder_list['raw'][foldertype]
        if not os.path.isdir(source_dir):
            return HttpResponse(content="Selected folder does currently not exist and cant be accessed.", status=500)

        dir_content = list(tempfolders_content[foldertype].values())

        return JsonResponse({"content": dir_content})

    def retrieve_content_only_convertable(self, foldertype):
        """Only nc files from folder that are potentially tif-convertable,
        """
        source_dir = folder_list['raw'][foldertype]
        if not os.path.isdir(source_dir):
            return HttpResponse(content="Selected folder does currently not exist and cant be accessed.", status=500)

        helper = []
        for el in tempfolders_content[foldertype].values():
            if el['filesuffix'] != '.nc':
                continue

            if el['fileinfo'] is None:
                helper.append(el)
            elif el['fileinfo']['tif_convertable']:
                helper.append(el)

        return JsonResponse({"content": helper})


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

        source_dir = folder_list['raw'][foldertype]
        filepath = os.path.join(source_dir, filename)

        if filetype == 'tif':
            return self.serve_tif_file(filepath, filename, foldertype)
        else:
            return self.serve_file(filepath, filename)

        # if filetype == 'nc':
        #     return self.serve_file(filepath, filename)
        # elif filetype == 'tif':
        #     return self.serve_tif_file(filepath, filename, foldertype)
        # elif filetype == 'dat':
        #     return self.serve_file(filepath, filename)
        # else:
        #     # this should never be reached... only for readability/when adding more filetypes
        #     return HttpResponse(content="Unknown filetype param value", status=400)

        # try:
        #     with open(os.path.join(source_dir, filename), "rb") as test_file:
        #         response = HttpResponse(content=test_file)
        #         response["Content-Disposition"] = f'attachment; filename="{filename}"'

        #         return response
        # except Exception:
        #     return HttpResponse(204)

    def serve_file(self, filepath, filename):
        # ==== this is for local testing

        # just for reference:
        # this -> content_type='application/octet-stream' fixed the decode error

        response = None
        with open(filepath, "rb") as test_file:
            response = HttpResponse(content=test_file.read(), content_type='application/octet-stream')
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

        if response is not None:
            return response
        else:
            return HttpResponse(content="Could not read the file content", status=500)
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
            succ, msg = extract_ncfile_metadata(filename, folder_list['raw'][foldertype], foldertype, force_update=True)
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
        if not is_temp_file_cached(filename, foldertype, temp_doc):
            update_tif = True

        if update_tif:
            succ, msg = cache_tif_from_nc(filename, foldertype, temp_doc)
            if not succ:
                # The raw file could not be converted
                # print(f"The raw file could not be converted. Reason: {msg}")
                return HttpResponse(content=f"The raw file could not be converted. Reason: {msg}", status=500)

        # update file in tempfolders_content
        if update_doc or update_tif:
            update_tempfolder_file(foldertype, filename)

        tif_filename = copy_filename_as_tif(filename)
        cache_dir = folder_list['cache'][foldertype]
        tif_filepath = os.path.join(cache_dir, tif_filename)

        return self.serve_file(tif_filepath, tif_filename)


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
                    "file_id": file.variable.variable_abbr
                    + "_"
                    + str(climateDatasetCollection.id)
                    + "_"
                    + str(file.id),
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
    TempResultFile.objects.all().delete()


def init_temp_results_folders(force_update=False, delete_all=False):
    if delete_all:
        delete_all_temp_results()

    folder_categories = folder_list['raw'].keys()
    created_objs_counter = 0
    for cat in folder_categories:
        print(f"Initiating TempResultFiles folder with category: {cat}")
        folder_root_path = folder_list['raw'][cat]
        filenames = os.listdir(folder_root_path)
        for name in filenames:
            filepath = os.path.join(folder_root_path, name)

            if not check_temp_result_filesize(filepath):
                # if file exceeds size limit, we do not extract metadata
                succ, msg = extract_ncfile_lite(name, folder_root_path, cat, force_update=force_update)
                if not succ:
                    # print(f"Failed to extract lite on filename: {name} in category: {cat}")
                    # print(f"Reason: {msg}")
                    continue
                else:
                    created_objs_counter += 1
            else:
                succ, msg = extract_ncfile_metadata(name, folder_root_path, cat, force_update=force_update)

                if not succ:
                    # print(f"Failed to extract metadata on filename: {name} in category: {cat}")
                    # print(f"Reason: {msg}")
                    continue
                else:
                    created_objs_counter += 1

            # post creation handling (?)
    print(f"Finished TempResultFiles Init. Created {created_objs_counter} database objects.")


def update_all_tempfolders():
    for foldertype in TEMP_FOLDER_TYPES:
        update_tempfolder_by_type(foldertype)

    print(tempfolders_content)


# delete_all_temp_results()
# init_temp_results_folders()
update_all_tempfolders()
