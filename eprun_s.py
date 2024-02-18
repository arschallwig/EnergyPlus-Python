# eprun_s.py    script for executing single-building EnergyPlus simulations through its Python API
# usage         python3 eprun_s.py <city> <year> <climate> <buildingID>
#               python3 eprun_s.py detroit 2040 rcp45 001

import argparse 
import sys 
import os
import glob
import multiprocessing as mp
from multiprocessing import Pool
import time

# Source EP
ep_install_path = "/usr/local/EnergyPlus-23-2-0/"
sys.path.append(ep_install_path)
from pyenergyplus.api import EnergyPlusAPI

# Parse input arguments 
parser = argparse.ArgumentParser(description="Required eprun_s Arguments")

parser.add_argument('--city', '-c', help='city name (baltimore|boston|dallas|detroit|minneapolis|orlando|phoenix|seattle)', type=str, required=True)
parser.add_argument('--year', '-y', help='4-digit year', type=str, required=True)
parser.add_argument('--climate', '-w', help='climate scenario (historical|rcp45|rcp85)', type=str, required=True)
parser.add_argument('--id', '-i', help='3-digit building ID', type=str, required=True)

args = parser.parse_args()

city = args.city
year = args.year
climate = args.climate
id = args.id

cwd = os.getcwd()

# Query input idf
idf_path = 'buildings/' + city + '/idf/' + id + '.idf'

# Query input epw
epw_search_path = 'weather/' + city + '/' + climate + '/'
epw_path = glob.glob(epw_search_path + year + '*')[0]
if not epw_path:
    print('Error: epw file not found')

# Set output path
output_path = 'output/' + city + '/' + climate + '/' + year + '/' + city + id # run in arschall/<top level dir> so I run arschall/EPpy/ ... ls here has weather building output


# Prepare api
api = EnergyPlusAPI()
print("EnergyPlus Version: " + str(api.functional.ep_version()))

# Begin execution
state = api.state_manager.new_state()
v = api.runtime.run_energyplus(state, ['-d', output_path, '-w', epw_path, idf_path])
if v != 0:
    print("EnergyPlus Simulation Failed")
    sys.exit(1)
