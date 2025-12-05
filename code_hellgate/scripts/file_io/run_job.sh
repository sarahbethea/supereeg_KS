#!/bin/bash

# DO NOT MODIFY THIS FILE!
# MODIFY config.py AND create_and_submit_jobs.py AS NEEDED

#SBATCH --job-name=file_io_npz_bo

#SBATCH --output=file_io_npz_bo%A_%a.out
#SBATCH --error=file_io_npz_bo%A_%a.err

#SBATCH --output=/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/file_io/file_io_npz_bo_log.txt
#SBATCH --error=/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/file_io/file_io_npz_bo_error.txt

#SBATCH --nodes=1

#SBATCH --cpus-per-task=5

#SBATCH --mem-per-cpu=6gb

#SBATCH --mail-user=jose.carmona-sanchez@umconnect.umt.edu

source /opt/conda/etc/profile.d/conda.sh

conda activate supereeg_env

# set the working directory *of the job* to the specified start directory
cd <config['startdir']>

# run the job
<config['cmd_wrapper']> <job_command> 

# note: job_command is reserved for the job command; it should not be specified in config.py

