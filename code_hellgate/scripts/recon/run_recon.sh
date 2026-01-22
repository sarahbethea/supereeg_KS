#!/bin/bash -l

# DO NOT MODIFY THIS FILE!
# MODIFY config.py AND create_and_submit_jobs.py AS NEEDED

#SBATCH --job-name=recon_submit

#SBATCH --nodes=1

#SBATCH --cpus-per-task=3

#SBATCH --mem-per-cpu=10gb

#SBATCH --mail-type=END,FAIL

#SBATCH --mail-user=jose.carmona-sanchez@umconnect.umt.edu

source /opt/conda/etc/profile.d/conda.sh

conda activate supereeg_env

# set the working directory *of the job* to the specified start directory

python /mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/recon/recon_job_submit.py 5