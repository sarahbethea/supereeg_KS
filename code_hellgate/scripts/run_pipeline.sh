#!/bin/bash -l

# DO NOT MODIFY THIS FILE!
# MODIFY config.py AND create_and_submit_jobs.py AS NEEDED

#SBATCH --job-name=supereeg_pipeline

#SBATCH --output=/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/pipeline_log.txt
#SBATCH --error=/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/pipeline_error.txt

#SBATCH --nodes=1

#SBATCH --cpus-per-task=3

#SBATCH --mem-per-cpu=6gb

#SBATCH --mail-type=END,FAIL

#SBATCH --mail-user=jose.carmona-sanchez@umconnect.umt.edu

source /opt/conda/etc/profile.d/conda.sh

conda activate supereeg_env

# set the working directory *of the job* to the specified start directory

python /mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/pipeline_JCS.py