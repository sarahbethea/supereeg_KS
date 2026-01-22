#!/bin/bash

# DO NOT MODIFY THIS FILE!
# MODIFY config.py AND create_and_submit_jobs.py AS NEEDED

#SBATCH --job-name=ave_mats

#SBATCH --output=ave_mats%A_%a.out
#SBATCH --error=ave_mats%A_%a.err

#SBATCH --output=/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/ave_mats/avemats_log.txt
#SBATCH --error=/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/ave_mats/avemats_error.txt

#SBATCH --nodes=1

#SBATCH --cpus-per-task=5

#SBATCH --mem-per-cpu=10gb

#SBATCH --mail-type=FAIL

#SBATCH --mail-user=jose.carmona-sanchez@umconnect.umt.edu

source /opt/conda/etc/profile.d/conda.sh

conda activate supereeg_env

cd <config['startdir']>

# run the job
<config['cmd_wrapper']> <job_command> #note: job_command is reserved for the job command; it should not be specified in config.py
