import reprlib
import sys
import importlib.util
from pathlib import Path


def import_dict_from_path(directory_path, filename='config.py', dict_name='my_dict'):
    """
    Import a dictionary from a specific directory
    
    Args:
        directory_path: Path to the directory containing the Python file
        filename: Name of the Python file (default: 'config.py')
        dict_name: Name of the dictionary variable (default: 'my_dict')
    
    Returns:
        The dictionary object
    """
    # Construct full file path
    file_path = Path(directory_path) / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Create a unique module name based on the path
    module_name = f"config_{Path(directory_path).stem}_{hash(str(file_path))}"
    
    # Load the module
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Get the dictionary
    if not hasattr(module, dict_name):
        raise AttributeError(f"Dictionary '{dict_name}' not found in {file_path}")
    
    return getattr(module, dict_name)

#path for file where pipeline scripts live (file_io, pyFR, etc)
scripts_path = "/home/josecs/miniconda3/envs/supereeg_env/supereeg_JCS/code_hellgate/scripts"

#path where you want to save the results of pipeline
pipeline_results_path = "/home/josecs/Desktop/supereeg_env"

#path where initial data lives to start the pipeline (file_io input data)
file_io_data_path = "/home/josecs/Desktop/supereeg_env"

#Will you be running on your local machine or on hellgate cluster? (if local type in '_local' if cluster make None)
local_or_host = "_local"


pipeline_steps = ["pyFR_locs","full_mats","ave_mats","recon"]

config = import_dict_from_path(f"{scripts_path}/file_io", 'config.py', 'config')
config['datadir'] = file_io_data_path
config['workingdir'] = pipeline_results_path+'/bo'
config['startdir'] = pipeline_results_path
config['template'] = scripts_path+"/file_io" + f"run_job{local_or_host}.sh"

# Open the config dict in write mode and overwrite its content
with open(f"{scripts_path}/file_io/config.py", "w") as f:
    # Use repr() to get the string representation of the dictionary
    f.write(f"config = {repr(config)}")



# Setup config file for pyFR
config = import_dict_from_path(f"{scripts_path}/pyFR_locs", 'config.py', 'config')

config['datadir'] = pipeline_results_path+'/bo'
config['workingdir'] = pipeline_results_path+"/pyFR_locs"
config['startdir'] = pipeline_results_path
config['template'] = scripts_path+"/pyFR_locs"+ f"run_job{local_or_host}.sh"

# Open the config dict in write mode and overwrite its content
with open(f"{scripts_path}/pyFR_locs/config.py", "w") as f:
    # Use repr() to get the string representation of the dictionary
    f.write(f"config = {repr(config)}")



# Setup config file for full_mats
config = import_dict_from_path(f"{scripts_path}/full_mats", 'config.py', 'config')

config['datadir'] = pipeline_results_path+'/bo'
config["pyFR_locs"] = pipeline_results_path+"/pyFR_locs"
config['workingdir'] = pipeline_results_path+"/full_mats"
config['startdir'] = pipeline_results_path
config['template'] = scripts_path+"/full_mats"+ f"run_job{local_or_host}.sh"

# Open the config dict in write mode and overwrite its content
with open(f"{scripts_path}/full_mats/config.py", "w") as f:
    # Use repr() to get the string representation of the dictionary
    f.write(f"config = {repr(config)}")


# Setup config file for ave_mats
config = import_dict_from_path(f"{scripts_path}/ave_mats", 'config.py', 'config')

config['datadir'] = pipeline_results_path + "/full_mats/results/union"
config['workingdir'] = pipeline_results_path+"/ave_mats"
config['startdir'] = pipeline_results_path
config['template'] = scripts_path+"/ave_mats"+ f"run_job{local_or_host}.sh"

# Open the config dict in write mode and overwrite its content
with open(f"{scripts_path}/ave_mats/config.py", "w") as f:
    # Use repr() to get the string representation of the dictionary
    f.write(f"config = {repr(config)}")


# Setup config file for recon
config = import_dict_from_path(f"{scripts_path}/recon", 'config.py', 'config')

config['datadir'] = pipeline_results_path+'/bo'
config['workingdir'] = pipeline_results_path+"/recon"
config['startdir'] = pipeline_results_path
config['modeldir'] = pipeline_results_path + "/full_mats/results/union"
config['template'] = scripts_path+"/ave_mats"+ f"run_job{local_or_host}.sh"

# Open the config dict in write mode and overwrite its content
with open(f"{scripts_path}/recon/config.py", "w") as f:
    # Use repr() to get the string representation of the dictionary
    f.write(f"config = {repr(config)}")


