# eprun_s.py    script for executing multi-building EnergyPlus simulations through its Python API
# usage         python3 eprun_s.py <city> <year> <climate> 
#               python3 eprun_s.py detroit 2040 rcp45 

import argparse 
import sys 
import os
import glob
from pathlib import Path
import time
import xml.etree.ElementTree as ET
import shutil
import tqdm 
import multiprocessing
import math 
from contextlib import redirect_stdout, redirect_stderr

class Job:
    def __init__(self, ID, bldg_id, bldg_dir, idf, city, scenario, ep_install_path, verbose):
        # require initialization with the folder of the files for the building
        self.id = ID
        self.idf_path = idf
        self.bldg_id = bldg_id
        self.bldg_dir = bldg_dir
        self.ep_install_path = ep_install_path
        self.verbose = verbose

        self.city = city    
        self.weather_scenario = scenario

        self.filebasename = None
        self.epw_path = None
        self.xml_path = None
        self.output_path = None

def get_attrib_text(root, attrib):
    """Get the attribute's text from the xml file"""
    for element in root.iter():
        if attrib in element.tag:
            return element.text


def find_epws_from_xml(jobs):
    # find the xml file to determine which weather (epw) file was used to generate the IDF file and thus which weather to simulate
    ET.register_namespace("", "http://hpxmlonline.com/2019/10")
    ET.register_namespace("xsi", 'http://www.w3.org/2001/XMLSchema-instance')
    ET.register_namespace("", 'http://hpxmlonline.com/2019/10')   

    for job in tqdm.tqdm(jobs, total=len(jobs), desc="Finding EPW files from XML files", smoothing=0.01):
    # for job in jobs:
        xml_path = job.idf_path.split(".idf")[0] + ".xml"
        if os.path.exists(xml_path):
            job.xml_path = xml_path
            tree = ET.parse(job.xml_path)
            root = tree.getroot()
            job.epw_path = get_attrib_text(root=root, 
                            attrib='EPWFilePath') 
            
            if not os.path.exists(job.epw_path): raise IOError(f"EPW file for bldg not found: {job.epw_path}")

        else: raise IOError(f"XML file for building could not be found: {xml_path}")
    
    return jobs


def generate_simulation_jobs(**kwargs):
    print('Generating job list for simulations..')
    city = kwargs.get('city')
    climate = kwargs.get('climate')

    # Query input idf
    idf_dir = os.path.join(kwargs.get('buildings_folder'), climate, city)
    if not os.path.exists(idf_dir): raise IOError(f"IDF directory not found: {idf_dir}")
    # idf_files = glob.glob(idf_dir + '/*.idf')
    # idf_ids = [Path(ifile).stem for ifile in idf_files]  

    jobs = []       # create list of jobs for parrellel processing 
    id = 0
    directories = glob.glob(f"{idf_dir}/*")
    for bldg_dir in tqdm.tqdm(directories, total=len(directories), desc="Finding IDF files", smoothing=0.01):
    # for bldg_dir in glob.glob(f"{idf_dir}/*"):
        # Construct the path to all *.idf files within the bldg_dir
        files = glob.glob(f"{bldg_dir}/*.idf")

        for idf in files:
            bldg_dir = os.path.basename(bldg_dir)
            bldg_id = os.path.basename(idf).split(".idf")[0]    # get the folder name of the building as the bldg id
            jobs.append(Job(id, bldg_id, bldg_dir, idf, city, climate, kwargs.get('ep_install_path'), kwargs.get('verbose')))
            id += 1

    if len(jobs) == 0:
        raise OSError('No jobs to run. Skipping simulation.')
    else: 
        # the current upstream workflow generates an IDF file for each weather file to be simulated 
        # so we check for the existence of those weather EPW files to run in simulation
        jobs = find_epws_from_xml(jobs)     
            
        run_jobs = []
        # Set output and idf path
        # print('\nFinding output folders.') 
        for job in tqdm.tqdm(jobs, total=len(jobs), desc="Checking output folders", smoothing=0.01):
            job.output_path = os.path.join(kwargs.get('output_folder'), climate, city, job.bldg_dir, job.bldg_id) 

            if not os.path.exists(job.output_path):
                if kwargs.get('verbose'): print(f'Creating output directory {job.output_path}')
                os.makedirs(job.output_path)  
                run_jobs.append(job)
            
            elif os.path.exists(job.output_path) and kwargs.get('overwrite_output'):
                if kwargs.get('verbose'): print(f'\tWarning: Output files being overwritten: {job.output_path}')
                shutil.rmtree(job.output_path)  
                os.makedirs(job.output_path)  
                run_jobs.append(job)

            elif os.path.exists(job.output_path) and not kwargs.get('overwrite_output'):
                if kwargs.get('verbose'): print(f'\tWarning: Output files exist in output folder and overwrite is false. Skipping job: {job.weather_scenario}/{job.city}/{job.bldg_id}')
        
        if len(jobs) == 0:
            raise OSError('All output files exist and overwite is false. No jobs to simulate.')
    
    print(f"Found {len(run_jobs)} buildings to simulate.")
    return run_jobs 


def run_job(job):
    # Source EP
    # Prepare api
    # Execute simulation 

    sys.path.append(job.ep_install_path)
    from pyenergyplus.api import EnergyPlusAPI      # import once the pyenergyplus path is added 
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()
    if not job.verbose: api.runtime.set_console_output_status(state, False)
    v = api.runtime.run_energyplus(state, ['-d', job.output_path, '-w', job.epw_path, job.idf_path])
    if v != 0:
        print("EnergyPlus Simulation Failed")
        sys.exit(1)
    # state.delete_state()

def run_energyplus_simulations(**kwargs):
    output_folder = kwargs.get('output_folder')
    if not os.path.exists(output_folder):
        if kwargs.get('verbose'): print(f'Creating output folder {kwargs.get('output_folder')}')
        os.mkdir(output_folder)

    if kwargs.get('overwrite'): 
        print('Caution: Overwrite is True. If existing output files are found they will be overwritten. If overwrite chosen in error, cancel job.')
        time.sleep(10)

    else: print('Caution: Overwrite is False: If existing output files are found, those jobs will be skipped.')

    # Generate list of simulation jobs to run 
    jobs = generate_simulation_jobs(**kwargs)

    # Iterative approach (could be parallelized for increased performance)
    start_time = time.time()

    # Setup the job pool
    # at least one CPU core, up to max_cpu_load * num_cpu_cores, no more cores than jobs
    num_cpus = max(min( math.floor( kwargs.get('max_cpu_load') * multiprocessing.cpu_count()), len(jobs)), 1)    
    pool = multiprocessing.Pool(processes=num_cpus)
    no_jobs = len(jobs)
    
    # Execute the job pool and track progress with tqdm progress bar
    print(f'Generating {len(jobs)} .idf files using {num_cpus} CPU cores')
    for _ in tqdm.tqdm(pool.imap_unordered(run_job, jobs), total=no_jobs, desc="Running E+ Simulations", smoothing=0.01):
        pass

    # for job in jobs: 
    #     run_job(job)

    print('\n')
    print('-----EnergyPlus Simulation Summary-----\n\tSimulated ' + str(len(jobs)) + ' buildings\n\tExecution time: ' + str(time.time() - start_time) + ' s')


if __name__ == "__main__":
    # Parse input arguments if called from command line 
    parser = argparse.ArgumentParser(description="Required eprun_s Arguments")

    parser.add_argument('--city', '-c', help='city name (baltimore|boston|dallas|detroit|minneapolis|orlando|phoenix|seattle)', type=str, required=True)
    parser.add_argument('--climate', '-w', help='climate scenario (historical|rcp45|rcp85)', type=str, required=True)
    parser.add_argument('--ep_install_path', '-epp', help='location of the EnergyPlus install folder that has pyenergyplus', type=str, required=True)
    parser.add_argument('--buildings_folder', '-bldgs_fldr', help='location of the buildings folder', type=str, required=True)
    parser.add_argument('--weather_folder', '-wthr_fldr', help="Location of the weather scenarios", type=str, required=True)
    parser.add_argument('--output_folder', '-o_fldr', help="Output folder", type=str, required=True)
    parser.add_argument('--overwrite_output', '-overwrite', action='store_true', default=False, help="Overwrite existing output")
    parser.add_argument('--verbose', '-v', action='store_true', default=False, help="Verbose output")


    args = parser.parse_args()

    run_energyplus_simulations(**vars(args))

