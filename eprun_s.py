# eprun_s.py    script for executing multi-building EnergyPlus simulations through its Python API
# usage         python3 eprun_s.py <city> <year> <climate> 
#               python3 eprun_s.py detroit 2040 rcp45 

import argparse 
import sys 
import os
import glob
from pathlib import Path
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
parser.add_argument('--directory', '-d', help='location of base directory where weather/ buildings/ and output/ are', type=str, required=True)

args = parser.parse_args()

city = args.city
year = args.year
climate = args.climate
tl_dir = args.directory

cwd = os.getcwd()

# Query input idf
idf_dir = tl_dir + '/buildings/' + city + '/idf/'
idf_files = glob.glob(idf_dir + '*.idf')
idf_ids = [Path(ifile).stem for ifile in idf_files]  

# Query input epw
epw_search_path = tl_dir + '/weather/' + city + '/' + climate + '/'
epw_path = glob.glob(epw_search_path + year + '*')[0]
if not epw_path:
    print('Error: epw file not found')

# Prepare api
api = EnergyPlusAPI()
print("EnergyPlus Version: " + str(api.functional.ep_version()))

# Iterative approach (could be parallelized for increased performance)
start_time = time.time()
for idf_id in idf_ids:
    # Set output and idf path
    output_path = tl_dir + '/output/' + city + '/' + climate + '/' + year + '/' + city + idf_id # run in arschall/<top level dir> so I run arschall/EPpy/ ... ls here has weather building output
    idf_path = idf_dir + idf_id + '.idf'

    # Begin execution
    state = api.state_manager.new_state()
    v = api.runtime.run_energyplus(state, ['-d', output_path, '-w', epw_path, idf_path])
    if v != 0:
        print("EnergyPlus Simulation Failed")
        sys.exit(1)

print('\n')
print('-----EnergyPlus Simulation Summary-----\n\tSimulated ' + str(len(idf_ids)) + ' buildings\n\tExecution time: ' + str(time.time() - start_time) + ' s\n\tOutputs in ' + tl_dir + '/output/' + city + '/' + climate + '/' + year + '/')