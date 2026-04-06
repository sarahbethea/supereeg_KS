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


################CHANGE##CODE###################CHANGE##CODE##################CHANGE##CODE#########################################
#path for file where pipeline scripts live (file_io, pyFR, etc) aka scrpts directory
scripts_path = "/home/josecs/miniconda3/envs/supereeg_env/supereeg_JCS/code_hellgate/scripts"

#path where you want to save the results of pipeline
pipeline_results_path = "/home/josecs/Desktop/supereeg_env"

#path where initial data lives to start the pipeline (file_io input data)
file_io_data_path = "/home/josecs/Desktop/supereeg_env"

#Will you be running the pipeline on your local machine? (type in True or False)
local_check = True
################CHANGE##CODE########################CHANGE##CODE#################CHANGE##CODE#####################################

pipeline_steps = ["file_io","pyFR_locs","full_mats","ave_mats","recon"]

config = import_dict_from_path(f"{scripts_path}/file_io", 'config.py', 'config')
config['datadir'] = file_io_data_path
config['workingdir'] = pipeline_results_path+'/bo'
config['startdir'] = pipeline_results_path
if local_check:
    config['template'] = scripts_path+"/file_io/run_job_local.sh"
else:
    config['template'] = scripts_path+"/file_io/run_job.sh"
# runtime options
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)
config['modules'] = "(\"python/3.13\")"  # separate each module with a space and enclose in (escaped) double quotes

# Open the config dict in write mode and overwrite its content
with open(f"{scripts_path}/file_io/config.py", "w") as f:
    # Use repr() to get the string representation of the dictionary
    f.write(f"config = {repr(config)}")



# Setup config file for pyFR
config = import_dict_from_path(f"{scripts_path}/pyFR_locs", 'config.py', 'config')

config['datadir'] = pipeline_results_path+'/bo'
config['workingdir'] = pipeline_results_path+"/pyFR_locs"
config['startdir'] = pipeline_results_path
if local_check:
    config['template'] = scripts_path+"/pyFR_locs/run_job_local.sh"
else:
    config['template'] = scripts_path+"/pyFR_locs/run_job.sh"
# runtime options
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)
config['modules'] = "(\"python/3.13\")"  # separate each module with a space and enclose in (escaped) double quotes

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
if local_check:
    config['template'] = scripts_path+"/full_mats/run_job_local.sh"
else:
    config['template'] = scripts_path+"/full_mats/run_job.sh"
# runtime options
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)
config['modules'] = "(\"python/3.13\")"  # separate each module with a space and enclose in (escaped) double quotes

# Open the config dict in write mode and overwrite its content
with open(f"{scripts_path}/full_mats/config.py", "w") as f:
    # Use repr() to get the string representation of the dictionary
    f.write(f"config = {repr(config)}")


# Setup config file for ave_mats
config = import_dict_from_path(f"{scripts_path}/ave_mats", 'config.py', 'config')

config['datadir'] = pipeline_results_path + "/full_mats/results/union"
config['workingdir'] = pipeline_results_path+"/ave_mats"
config['startdir'] = pipeline_results_path
if local_check:
    config['template'] = scripts_path+"/ave_mats/run_job_local.sh"
else:
    config['template'] = scripts_path+"/ave_mats/run_job.sh"
# runtime options
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)
config['modules'] = "(\"python/3.13\")"  # separate each module with a space and enclose in (escaped) double quotes

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
if local_check:
    config['template'] = scripts_path+"/recon/run_job_local.sh"
else:
    config['template'] = scripts_path+"/recon/run_job.sh"
# runtime options
config['cmd_wrapper'] = "python"  # replace with actual command wrapper (e.g. matlab, python, etc.)
config['modules'] = "(\"python/3.13\")"  # separate each module with a space and enclose in (escaped) double quotes

# Open the config dict in write mode and overwrite its content
with open(f"{scripts_path}/recon/config.py", "w") as f:
    # Use repr() to get the string representation of the dictionary
    f.write(f"config = {repr(config)}")


