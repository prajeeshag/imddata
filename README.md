
# imddata
![PyPI - Version](https://img.shields.io/pypi/v/imddata)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
---

Download India Meteorological Department (IMD) gridded rainfall and minimum and maximum temperature data as netCDF files from your terminal.

## Installation
```bash
$ pip install imddata
```

## Usage
For usage instructions, run
```bash
$ imddata --help
```


example:
```bash
$ imddata --name tmax --syear 2020 --eyear 2022
$ ls
IMD_tmax_2020.nc
IMD_tmax_2021.nc
IMD_tmax_2022.nc
```

With a custom filename prefix:
```bash
$ imddata --name tmax --syear 2020 --eyear 2022 --filename-prefix tmin_data
$ ls
tmin_data_2020.nc
tmin_data_2021.nc
tmin_data_2022.nc
```
