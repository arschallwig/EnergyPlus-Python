import eprun_s
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
            
    arguments = {
        'cities': ['Dallas'], 
        'climate_scenarios': ['historical_1980-2020'],
        }

    run_args = {
        'ep_install_path': '/Applications/OpenStudio-3.4.0/EnergyPlus',

        # Repository example files 
        # 'buildings_folder': '/Users/camilotoruno/Documents/GitHub/EnergyPlus-Python/Buildings',
        # 'weather_folder': '/Users/camilotoruno/Documents/GitHub/EnergyPlus-Python/TGWEPWs',
        # 'output_folder': '/Users/camilotoruno/Documents/GitHub/EnergyPlus-Python/simulations',

        # Turbo locations
        'weather_folder': '/Volumes/seas-mtcraig/EPWFromTGW/TGWEPWs',
        # 'output_folder': 'Volumes/seas-mtcraig/ctoruno/Buildings_Dallas_downsample_simulations',

        # Local locations 
        'output_folder': '/Users/camilotoruno/Documents/local_research_data/Buildings_Dallas_downsample_simulations',
        'buildings_folder': '/Users/camilotoruno/Documents/local_research_data/Buildings_Dallas_downsample_structured',

        'overwrite_output': True, 
        'verbose': False,
        "max_cpu_load": 0.99,      # must be in the range [0, 1]. The value 1 indidcates all CPU cores, 0 indicates 1 CPU core
        'batch_size': 10,           # number of jobs in a batch for multicore processing. Intended to reduce the amount of context switching for cores.
        'city': None,       # initialize
        'climate': None,    # initialize
        }

    for scenario in arguments['climate_scenarios']:
        for city in arguments['cities']:
            run_args['city'] = city
            run_args['climate'] = scenario
            eprun_s.run_energyplus_simulations(**run_args)
