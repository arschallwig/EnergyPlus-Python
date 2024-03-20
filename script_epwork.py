import eprun_s
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
            
    arguments = {
        'cities': ['Dallas'], 
        'climate_scenarios': ['historical_1980-2020'],
        }

    run_args = {
        'city': None, 
        'climate': None,
        'directory': '/Users/camilotoruno/Documents/GitHub/EnergyPlus-Python',
        'ep_install_path': '/Applications/OpenStudio-3.4.0/EnergyPlus',
        'buildings_folder': '/Users/camilotoruno/Documents/local_research_data/Buildings',
        'weather_folder': '/Volumes/seas-mtcraig/EPWFromTGW/TGWEPWs',
        'output_folder': '/Users/camilotoruno/Documents/local_research_data/simulations ',
        'overwrite_output': True, 
        'verbose': True,
        "max_cpu_load": 0.99      # must be in the range [0, 1]. The value 1 indidcates all CPU cores, 0 indicates 1 CPU core
        }

    for scenario in arguments['climate_scenarios']:
        for city in arguments['cities']:
            run_args['city'] = city
            run_args['climate'] = scenario
            eprun_s.run_energyplus_simulations(**run_args)
