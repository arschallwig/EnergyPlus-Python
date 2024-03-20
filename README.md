# EnergyPlus Python Simulation Pipeline

## eprun_s.py Example usage: 

Run: Using idf and schedule files generated by Restock to Energy Plus pipeline. 
Requires: schedule files in the same folder as the idf files (believe this is due to the IDF schedules not having relative file paths)
From base folder (repostory folder) call the command python eprun_s.py script 

```python eprun_s.py --city <City> --climate <weather_scenario> --ep_install_path <pyenergyplus location> --buildings_folder <buildings folder from ResStock to EnergyPlus workflow> --weather_folder <Location of weather scenarios> --output_folder <desired output folder>```

An example is ```python eprun_s.py --city Dallas --climate historical_1980-2020 --ep_install_path /Applications/OpenStudio-3.4.0/EnergyPlus --buildings_folder /Users/camilotoruno/Documents/local_research_data/Buildings --weather_folder /Volumes/seas-mtcraig/EPWFromTGW/TGWEPWs --output_folder /Users/camilotoruno/Documents/local_research_data/simulations --overwrite```

## script_epwork.py Setup:
In the arguments sections define the arguments for the eprun_s.py file as described above, and add the list of cities and climate scenarios to run the simulation for. 


