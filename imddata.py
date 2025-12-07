import enum
import typing as t
from pathlib import Path

import numpy as np
import pandas as pd  # type: ignore
import typer
import xarray as xr
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = typer.Typer(add_completion=False)

session = Session()
retry = Retry(
    total=5,  # retry up to 5 times
    connect=5,  # retry on connection errors
    read=5,  # retry on read timeout
    backoff_factor=1,  # sleep: 1s, 2s, 4s, ...
    allowed_methods=["GET", "POST"],
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)


class IMDData(enum.Enum):
    rain = "rain"
    tmin = "tmin"
    tmax = "tmax"


IYEAR = {
    "tmin": 1951,
    "tmax": 1951,
    "rain": 1901,
}


def lat(name: IMDData) -> xr.DataArray:
    if name == IMDData.rain:
        lat = np.linspace(6.5, 38.5, 129)
    else:
        lat = np.linspace(7.5, 37.5, 31)
    return xr.DataArray(
        lat,
        dims=("lat",),
        name="lat",
        attrs={"standard_name": "latitude", "units": "degrees_north"},
    )


def lon(name: IMDData):
    if name == IMDData.rain:
        lon = np.linspace(66.5, 100.0, 135)
    else:
        lon = np.linspace(67.5, 97.5, 31)
    return xr.DataArray(
        lon,
        dims=("lon",),
        name="lon",
        attrs={"standard_name": "longitude", "units": "degrees_east"},
    )


def end_year(value: str | int) -> int:
    if value == "<syear>":
        return 0
    else:
        return int(value)


@app.command()
def main(
    name: t.Annotated[
        IMDData,
        typer.Option(
            help=(
                "rainfall: rain, "
                + "minimum temperature: tmin, "
                + "maximum temperature: tmax"
            )
        ),
    ],
    syear: t.Annotated[int, typer.Option(help="start year")],
    eyear: t.Annotated[int, typer.Option(help="end year", parser=end_year)] = "<syear>",  # type: ignore
    filename_prefix: t.Annotated[
        str, typer.Option(help="filename prefix")
    ] = "IMD_<name>",
):
    data_type = "bin"
    missing_value = np.nan
    match name:
        case IMDData.rain:
            var = "rain"
            url = "https://imdpune.gov.in/cmpg/Griddata/rainfall.php"
            # data_type = "netcdf"
            description = "IMD 0.25 degree gridded rainfall"
            units = "mm/day"
            missing_value = -999.0
        case IMDData.tmax:
            var = "maxtemp"
            url = "https://imdpune.gov.in/cmpg/Griddata/maxtemp.php"
            description = "IMD 1 degree gridded maximum temperature"
            units = "degC"
            missing_value = 99.9
        case IMDData.tmin:
            var = "mintemp"
            url = "https://imdpune.gov.in/cmpg/Griddata/mintemp.php"
            description = "IMD 1 degree gridded minimum temperature"
            units = "degC"
            missing_value = 99.9
        case _:
            raise ValueError(f"Invalid name: {name}")

    if syear < IYEAR[name.value]:
        syear = IYEAR[name.value]
        print(f"Data not available before {syear}, starting from {syear}")  # noqa T201

    if filename_prefix == "IMD_<name>":
        filename_prefix = f"IMD_{name.value}"

    if eyear == 0:
        eyear = syear
    for year in range(syear, eyear + 1):
        outfile = f"{filename_prefix}_{year}.nc"
        if Path(outfile).exists():
            print(f"File already exists: {outfile}")  # noqa T201
            continue
        data = {var: year}
        print(f"Downloading {name} data for {year}")  # noqa T201
        response = session.post(url, data=data, proxies=None)
        response.raise_for_status()

        if data_type == "bin":
            nc_from_buffer(
                response.content,
                name.value,
                lon(name),
                lat(name),
                days_of_year(year),
                missing_value=missing_value,
                units=units,
                description=description,
                filename=outfile,
            )
        elif data_type == "netcdf":
            with open(outfile, "wb") as f:
                f.write(response.content)


def days_of_year(year: int) -> xr.DataArray:
    """Return an xarray time coordinate for all days in the given year."""
    times = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31", freq="D")

    return xr.DataArray(
        times, dims=("time",), name="time", attrs={"standard_name": "time"}
    )


def nc_from_buffer(
    buffer: bytes,
    varname: str,
    lon: xr.DataArray,
    lat: xr.DataArray,
    time: xr.DataArray,
    missing_value: float,
    units: str,
    description: str,
    filename: str,
):
    """Convert raw binary buffer → CF-compliant xarray.Dataset."""

    ntime, nlat, nlon = len(time), len(lat), len(lon)

    data = np.frombuffer(buffer, dtype=np.float32)
    data = data.reshape((ntime, nlat, nlon))

    da = xr.DataArray(
        data,
        dims=("time", "lat", "lon"),
        coords={"time": time, "lat": lat, "lon": lon},
        name=varname,
        attrs={
            "description": description or varname,
            "units": units,
            "missing_value": missing_value,
        },
    )
    ds = da.to_dataset()
    ds[varname].encoding["_FillValue"] = missing_value
    ds.attrs["Conventions"] = "CF-1.10"
    ds.to_netcdf(filename, unlimited_dims=["time"])


if __name__ == "__main__":
    # with open("file.bin", "rb") as f:
    #     buffer = f.read()
    # nc_from_buffer(
    #     buffer,
    #     "tmax",
    #     lon_temp(),
    #     lat_temp(),
    #     days_of_year(2000),
    #     missing_value=99.9,
    #     units="degC",
    #     description="IMD 1 degree gridded maximum temperature",
    #     filename="test.nc",
    # )
    app()
