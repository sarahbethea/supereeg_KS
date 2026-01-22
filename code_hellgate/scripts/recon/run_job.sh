#!/bin/bash -l

# DO NOT MODIFY THIS FILE!
# MODIFY config.py AND create_and_submit_jobs.py AS NEEDED

#SBATCH --job-name=recon

#SBATCH --output=recon%A_%a.out
#SBATCH --error=recon%A_%a.err

#SBATCH --output=/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/recon/recon_log.txt
#SBATCH --error=/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/recon/recon_error.txt

#SBATCH --nodes=1

#SBATCH --cpus-per-task=7

#SBATCH --mem-per-cpu=15gb

#SBATCH --mail-user=jose.carmona-sanchez@umconnect.umt.edu

# set the working directory *of this script* to the directory from which the job was submitted

source /opt/conda/etc/profile.d/conda.sh

conda activate supereeg_env

# set the working directory *of the job* to the specified start directory
cd <config['startdir']>

# run the job
<config['cmd_wrapper']> <job_command> #note: job_command is reserved for the job command; it should not be specified in config.py
