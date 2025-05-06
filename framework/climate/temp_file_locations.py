import os
from pathlib import Path
from typing import TypedDict

from django.conf import settings
# import logging
# logger = logging.getLogger('django')

# add comment

# keys that are folder names in TEMP_RAW and TEMP_CACHE
# TEMP_FOLDER_TYPES = [
#     "water_budget",
#     "water_budget_bias",
#     "kariba",
#     "vaal_CORDEX",
#     "vaal_CHIRPS",
#     "cmip6",
#     "paper",
#     "luanginga",
#     "ind_full",
#     "ind_slices20",
#     "ind_slices30",
#     "cmip6_raw",
#     "cmip6_raw_ind",
#     "era5_land",
#     "sftlf",
#     "orog"
# ]

TEMP_FOLDER_TYPES = [
    "CCAM_raw",
    "CCAM_raw_ind",
    "CCAM_bias",
    "CCAM_bias_ind",
    "CORDEX_bias",
    "CORDEX_bias_stat",
    "CORDEX_raw",
    "CORDEX_raw_stat",
    "CORDEX_raw_ind",
    "CORDEX_raw_ind_stat",
    "CORDEX_bias_ind",
    "CORDEX_bias_ind_stat",
    "CMIP6_raw",
    "CMIP6_raw_stat",
    "CMIP6_raw_ind",
    "CMIP6_raw_ind_stat",
    "CMIP6_bias",
    "CMIP6_bias_stat",
    "CMIP6_bias_ind",
    "CMIP6_bias_ind_stat",
    "CHIRPS",
    "vaal_CORDEX",
    "vaal_CHIRPS",
    "vaal_ERA5_LAND",
    "kunene_ERA5_LAND",
    "kunene_GLEAM",
    "kariba_CORDEX",
    "luanginga_CORDEX",
    "CORDEX_LANDSURF_ind_full",
    "CORDEX_LANDSURF_ind_slices20",
    "CORDEX_LANDSURF_ind_slices30",
    "GLEAM",
    "sftlf",
    "orog",
    "paper",
]


# SERVER paths
# TEMP_ROOT = "/opt/rbis/www/tippecc_data"  # not used atm
TEMP_RAW = "/data"  # path to raw directory (raw nc files)
TEMP_CACHE = "/data/_tmp_gateway/cache"  # path to cache directory (converted filetypes)
TEMP_URL = "/data/_tmp_gateway/url"  # path to url directory (wget requests storage)
URLTXTFILES_DIR = TEMP_URL

JAMS_TMPL_FILE = os.path.join(settings.BASE_DIR, "framework/climate/static/jams_tmpl.dat")

FileInfo = TypedDict(
    "FileInfo",
    {
        'filename': str,
        'filesize': str,
        'creation_date': str,
        'fileversion': str,
        'filesuffix': str,
        'in_limit_conversion': bool,
        'in_limit_download': bool,
        'dirty': bool,
        'dat_exists': bool,
        'tif_exists': bool,
        'tif_convertable': bool,
        'num_bands': int
    }
)

FolderInfo = TypedDict(
    "FolderInfo",
    {
        'last_update': float,
        'content': dict[str, FileInfo]
    }
)

# lookup dict for the paths of each foldertype
_folder_list = {}
_folder_list['raw'] = {}
_folder_list['cache'] = {}

# overwrite with paths in static/ when running on dev
if settings.DEV_LOCAL:
    # LOCAL paths
    TEMP_ROOT = settings.STATICFILES_DIRS[0]
    TEMP_RAW = os.path.join(TEMP_ROOT, "data/tmp/raw")
    TEMP_CACHE = os.path.join(TEMP_ROOT, "data/tmp/cache")
    TEMP_LOG = os.path.join(TEMP_ROOT, "data/tmp/log")
    TEMP_URL = os.path.join(TEMP_ROOT, "data/tmp/url")
    URLTXTFILES_DIR = TEMP_URL


for TEMP_FOLDER_TYPE in TEMP_FOLDER_TYPES:
    # print("SETTING PATH: ", os.path.join(TEMP_RAW, TEMP_FOLDER_TYPE))
    _folder_list['raw'][TEMP_FOLDER_TYPE] = os.path.join(TEMP_RAW, TEMP_FOLDER_TYPE)
    _folder_list['cache'][TEMP_FOLDER_TYPE] = os.path.join(TEMP_CACHE, TEMP_FOLDER_TYPE)


def temp_cat_filename(category: str, filename: str):
    """Used for accessing a TempResultFile.
    """
    return os.path.join(category, filename)


def copy_filename_as_tif(f: str):
    """Used for naming a tif file from a .nc filename.
    """
    return f"{Path(f).stem}.tif"


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
        folder = os.listdir(_folder_list['raw'][foldertype])
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


def tmp_raw_path(foldertype: str, filename: str = '') -> str:
    """Returns path to raw directory if dir exists. Appends filename
    if given. If dir does not exist, returns false.
    """
    try:
        dir_path = _folder_list['raw'][foldertype]
        if not os.path.isdir(dir_path):
            return False

        if filename != '':
            res = os.path.join(dir_path, filename)
        else:
            res = dir_path

        return res
    except Exception:
        return False


def tmp_raw_filepath(foldertype: str, filename: str) -> str:
    """Returns path to a given filename from a raw directory.
    Returns False if file does not exist.
    """
    try:
        dir_path = _folder_list['raw'][foldertype]
        file_path = os.path.join(dir_path, filename)
        if os.path.isfile(file_path):
            return file_path
        else:
            return False
    except Exception:
        return False


def tmp_cache_path(foldertype: str, filename: str = '') -> str:
    """Returns path to cache directory if dir exists. Appends filename
    if given. If dir does not exist, returns false.
    """
    try:
        dir_path = _folder_list['cache'][foldertype]
        if filename != '':
            res = os.path.join(dir_path, filename)
        else:
            res = dir_path

        return res
    except Exception:
        return False
