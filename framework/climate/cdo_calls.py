import sys

from cdo import Cdo


print("argument list", sys.argv)


def slice_bbox(file, file_out, lonmin, lonmax, latmin, latmax):
    cdo = Cdo()
    cdo.sellonlatbox(
        lonmin, lonmax, latmin, latmax, input=file, output=file_out, options="-f nc4"
    )


def slice_time(file, file_out, year_from, year_to):
    cdo = Cdo()
    cdo.seltimestep(year_from, year_to, input=file, output=file_out, options="-f nc4")


if sys.argv[1] == "bbox":
    file = sys.argv[2]
    file_out = sys.argv[3]
    lonmin = sys.argv[4]
    lonmax = sys.argv[5]
    latmin = sys.argv[6]
    latmax = sys.argv[7]
    slice_bbox(file, file_out, lonmin, lonmax, latmin, latmax)

if sys.argv[1] == "time":
    file = sys.argv[2]
    file_out = sys.argv[3]
    year_from = (int(sys.argv[4]) - int(sys.argv[6])) * 360
    year_from = (int(sys.argv[5]) - int(sys.argv[6])) * 360
    slice_time(file, file_out, year_from, year_from)
