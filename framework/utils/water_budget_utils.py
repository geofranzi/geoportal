import json
import os
from pathlib import Path
from subprocess import (PIPE, Popen,)

from django.conf import settings
from osgeo import gdal

from framework.climate.models import NcFile


test_file_name = "GERICS-REMO2015_v1_MOHC-HadGEM2-ES_pr_Afr_day_1970_2099__mm__yearsum__yearsum_mean_1980_2000-2080_2099.nc"

CACHED_TIFS_DIR = os.path.join(settings.STATICFILES_DIRS[0], 'cached_tifs')


def extract_file_metadata(filepath: str):
    if not os.path.isfile(filepath):
        return False

    process = Popen(["gdalinfo", filepath, "-json", "-mm"], stdout=PIPE, stderr=PIPE)
    # process = Popen(f"gdalinfo data/tif_data/{input_filename} -json")
    stdout, stderr = process.communicate()
    metadata = stdout.decode("utf-8")

    JSON_metadata = json.loads(metadata)

    if 'bands' not in JSON_metadata:
        return False

    complete_band_metadata = {}
    num_bands = len(JSON_metadata['bands'])

    try:
        for i, band_metadata in enumerate(JSON_metadata['bands']):
            band_collect = {}
            band_collect['min'] = band_metadata['computedMin']
            band_collect['max'] = band_metadata['computedMax']
            band_collect['NETCDF_DIM_time'] = band_metadata['metadata']['']['NETCDF_DIM_time']
            band_collect['index'] = i+1
            complete_band_metadata[str(i+1)] = band_collect
    except Exception:
        return False

    try:
        NcFile(filepath=filepath, num_bands=num_bands, band_metadata=complete_band_metadata).save()
    except Exception:
        return False

    print(complete_band_metadata)
    return True


def translate_nc_file_to_gtiff(filename_in: str, dir_in: str, dir_out: str):
    filepath_in = os.path.join(dir_in, filename_in)
    if not os.path.isfile(filepath_in):
        return False

    filename_out = Path(filename_in).stem + ".tif"
    filepath_out = os.path.join(dir_out, filename_out)

    print(f"filename_out: {filename_out}")
    print(f"filepath_in: {filepath_in}")
    print(f"filepath_out: {filepath_out}")
    ds = gdal.Open(filepath_in)
    gdal.Translate(filepath_out, ds, format='Gtiff')


def get_file_metadata(filepath: str):
    filtered_object: NcFile = NcFile.objects.get(filepath=filepath)
    print(f"FILTERED OBJECT: {filtered_object}")
    print(filtered_object.num_bands)


def is_tif_file_cached(filename: str):
    if os.path.isfile(os.path.join(CACHED_TIFS_DIR, filename)):
        return True
    else:
        return False

# extract_file_metadata(os.path.join(WATER_BUDGET_DIR, test_file_name))
# get_file_metadata(os.path.join(WATER_BUDGET_DIR, test_file_name))
