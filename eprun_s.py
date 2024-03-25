# eprun_s.py    script for executing multi-building EnergyPlus simulations through its Python API

import argparse 
import sys 
import os
import glob
import time
import xml.etree.ElementTree as ET
import shutil
import tqdm 
import multiprocessing
import math 


class Job:
    def __init__(self, ID, bldg_id, bldg_dir, idf, city, scenario, ep_install_path, verbose):
        # require initialization 
        self.id = ID
        self.idf_path = idf
        self.bldg_id = bldg_id
        self.bldg_dir = bldg_dir
        self.ep_install_path = ep_install_path
        self.verbose = verbose
        self.city = city    
        self.weather_scenario = scenario
        self.xml_path, self.epw_path = find_xml_epw(idf)       # find EPW file from XML file from IDF file

        # To be determined / found 
        self.filebasename = None
        self.output_path = None


def get_attrib_text(root, attrib):
    """Get the attribute's text from the xml file"""
    for element in root.iter():
        if attrib in element.tag:
            return element.text


def find_xml_epw(idf_path):
    # find the xml file to determine which weather (epw) file was used to generate the IDF file and thus which weather to simulate
    xml_path = idf_path.split(".idf")[0] + ".xml"

    if not os.path.exists(xml_path): raise RuntimeError(f"XML file for building could not be found: {xml_path}")
    else:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        epw_path = get_attrib_text(root=root, attrib='EPWFilePath') 
        if not os.path.exists(epw_path): raise RuntimeError(f"EPW file for bldg not found: {epw_path}")

    return xml_path, epw_path


def generate_simulation_jobs(**kwargs):
    """ 
    1) Generate a job for each IDF
    2) Check for existing simulated results for the IDF and whether overwrite is true
    """

    print('Generating job list for simulations..')
    city = kwargs.get('city')
    climate = kwargs.get('climate')

    # Query input idf
    idf_dir = os.path.join(kwargs.get('buildings_folder'), climate, city)
    if not os.path.exists(idf_dir): raise RuntimeError(f"IDF directory not found: {idf_dir}")

    jobs = []       # create list of jobs for parrellel processing 
    id = 0
    directories = glob.glob(f"{idf_dir}/*")
    for bldg_dir in tqdm.tqdm(directories, total=len(directories), desc="Finding IDF, XML, & EPW files", smoothing=0.01):   # for loop inside progoress bar

        for bldg_folder in glob.glob(f"{bldg_dir}/*"):
            # Construct the path to all *.idf files within the bldg_dir
            files = glob.glob(f"{bldg_folder}/*.idf")

            for idf in files:
                bldg_folder = os.path.basename(bldg_folder)
                bldg_id = os.path.basename(idf).split(".idf")[0]    # get the folder name of the building as the bldg id

                # the current upstream workflow generates an IDF file for each weather file to be simulated 
                # so we check for the existence of those weather EPW files to run in simulation. Job initialization automatically finds this EPW. 
                jobs.append(Job(id, bldg_id, bldg_folder, idf, city, climate, kwargs.get('ep_install_path'), kwargs.get('verbose')))
                id += 1

    if len(jobs) == 0: raise RuntimeError('No jobs to run. Skipping simulation.')
    
    else: 
        # Check whether output exists and whether to overwrite 
        run_jobs = []
        for job in tqdm.tqdm(jobs, total=len(jobs), desc="Checking output folders", smoothing=0.01):            # for loop inside progoress bar
            job.output_path = os.path.join(kwargs.get('output_folder'), climate, city, job.bldg_dir, job.bldg_id) 

            overwrite = kwargs.get('overwrite_output')
            if not os.path.exists(job.output_path):
                if kwargs.get('verbose'): print(f'Creating output directory {job.output_path}')
                os.makedirs(job.output_path)  
                run_jobs.append(job)
            
            elif os.path.exists(job.output_path) and overwrite:
                if kwargs.get('verbose'): print(f'\tWarning: Output files being overwritten: {job.output_path}')
                shutil.rmtree(job.output_path)  
                os.makedirs(job.output_path)  
                run_jobs.append(job)

            elif os.path.exists(job.output_path) and not overwrite:
                if kwargs.get('verbose'): print(f'\tWarning: Output files exist in output folder and overwrite is false. Skipping job: {job.weather_scenario}/{job.city}/{job.bldg_id}')
        
        if len(jobs) == 0: raise RuntimeError('All output files exist and overwite is false. No jobs to simulate.')
    
    print(f"Found {len(run_jobs)} buildings to simulate.")
    return run_jobs 


def run_job(job):
    """ Simulate a single building for a weather file """

    sys.path.append(job.ep_install_path)            # Source EP
    from pyenergyplus.api import EnergyPlusAPI      # import once the pyenergyplus path is added 

    api = EnergyPlusAPI()                           # Prepare api
    state = api.state_manager.new_state()
    if not job.verbose: api.runtime.set_console_output_status(state, False)

    v = api.runtime.run_energyplus(state, ['-d', job.output_path, '-w', job.epw_path, job.idf_path])        # Execute simulation 

    if v != 0:
        print("EnergyPlus Simulation Failed")
        sys.exit(1)

    api.state_manager.delete_state(state)           # required to free up memory 


def run_energyplus_simulations(idf_simulation_options, **kwargs):
    """ Main function """

    # Register XML namespaces for XML file reading / modifying (may not be necessary?)
    ET.register_namespace("", "http://hpxmlonline.com/2019/10")
    ET.register_namespace("xsi", 'http://www.w3.org/2001/XMLSchema-instance')
    ET.register_namespace("", 'http://hpxmlonline.com/2019/10')   

    output_folder = kwargs.get('output_folder')
    if not os.path.exists(output_folder):
        if kwargs.get('verbose'): print(f'Creating output folder {kwargs.get('output_folder')}')
        os.mkdir(output_folder)

    if kwargs.get('overwrite_output'): 
        print('Caution: Overwrite is True. If existing output files are found they will be overwritten. If overwrite chosen in error, cancel job.')
        time.sleep(10)

    else: print('Caution: Overwrite is False: If existing output files are found, those jobs will be skipped.')

    # Generate list of simulation jobs to run 
    jobs = generate_simulation_jobs(**kwargs)

    # if the user specified energy plus outputs, ensure they're set within the IDF file
    if len(idf_simulation_options) > 0:
        bldg_to_idf_repository = kwargs.get('ResStockToEnergyPlus_repository')
        if os.path.exists(bldg_to_idf_repository): sys.path.append(bldg_to_idf_repository)            # Source custom script
        else: raise RuntimeError(f'Cannot find ResStockToEnergyPlus repository for setting IDF simulation outputs {bldg_to_idf_repository}')

        import reset_idf_schedules_path      # import once the path is added 
        for job in jobs: job.idf = job.idf_path  # make compatible with upstream workflow function 
        reset_idf_schedules_path.set_EnergyPlus_Simulation_Output(jobs, idf_simulation_options, **kwargs)

    # Iterative approach (could be parallelized for increased performance)
    start_time = time.time()

    # Setup the job pool
    # at least one CPU core, up to max_cpu_load * num_cpu_cores, no more cores than jobs
    num_cpus = max(min( math.floor( kwargs.get('max_cpu_load') * multiprocessing.cpu_count()), len(jobs)), 1)    
    pool = multiprocessing.Pool(processes=num_cpus)
    no_jobs = len(jobs)

    # Execute the job pool and track progress with tqdm progress bar
    print(f'Simulating {no_jobs} .idf files using {num_cpus} CPU cores')
    for _ in tqdm.tqdm(pool.imap_unordered(run_job, jobs), total=no_jobs, desc="Running E+ Simulations", smoothing=0.01):
        pass

    # for job in jobs: 
    #     run_job(job)

    elapsed_time = time.time() - start_time
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)
    print('\n-----EnergyPlus Simulation Summary-----\n\tSimulated ' + str(len(jobs)) + ' buildings \n' + f'\tExecution time: {hours:02d}hr:{minutes:02d}min:{seconds:02d}sec')


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