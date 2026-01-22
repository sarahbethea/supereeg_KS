import supereeg as se
import sh
import socket
import time
import numpy as np
import os

if (socket.gethostname() == 'josecsOmarchy'):
    supereeg_env = "/home/josecs/Desktop/supereeg_env"
    fileIO_jobsubmit_path = "/home/josecs/miniconda3/envs/supereeg_env/supereeg_hellgate/code_hellgate/scripts/file_io/file_io_job_submit.py"
    pyFR_jobsubmit_path = "/home/josecs/miniconda3/envs/supereeg_env/supereeg_hellgate/code_hellgate/scripts/pyFR_locs/union_locs_job_submit.py"
    fullmats_jobsubmit_path = "/home/josecs/miniconda3/envs/supereeg_env/supereeg_hellgate/code_hellgate/scripts/full_mats/full_mats_job_submit.py"
    avemats_jobsubmit_path = "/home/josecs/miniconda3/envs/supereeg_env/supereeg_hellgate/code_hellgate/scripts/ave_mats/ave_mats_job_submit.py"
    reacon_jobsubmit_path = "/home/josecs/miniconda3/envs/supereeg_env/supereeg_hellgate/code_hellgate/scripts/recon/recon_job_submit.py"
else:
    supereeg_env = "/mnt/beegfs/projects/jc158347/supereeg_jcs/supereeg_env"
    fileIO_jobsubmit_path = "/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/file_io/file_io_job_submit.py"
    pyFR_jobsubmit_path = "/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/pyFR_locs/union_locs_job_submit.py"
    fullmats_jobsubmit_path = "/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/full_mats/full_mats_job_submit.py"
    avemats_jobsubmit_path = "/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/ave_mats/ave_mats_job_submit.py"
    reacon_jobsubmit_path = "/mnt/beegfs/projects/jc158347/supereeg_jcs/scripts/recon/recon_job_submit.py"

run = sh.Command('python')

rbf_widths = [40,50]

for i in rbf_widths:
    print(f"Running File_IO: lamda={i}")
    start_time_fileIO = time.time()
    run(fileIO_jobsubmit_path)
    end_time_fileIO = time.time()
    elapsed_time_fileIO = end_time_fileIO - start_time_fileIO
    print(f"Done running File_IO: lambda={i}")
    print(f"Total run time {elapsed_time_fileIO} sec\n")

    run_time = np.array([elapsed_time_fileIO])
    np.savez(supereeg_env+"/Total_Run_Time.npz",run_time)

    print(f"Running pyFR: lambda={i}")
    start_time_pyFR = time.time()
    run(pyFR_jobsubmit_path)
    end_time_pyFR = time.time()
    elapsed_time_pyFR = end_time_pyFR - start_time_pyFR
    print(f"Done running pyFR: lambda={i}")
    print(f"Total run time {elapsed_time_pyFR} sec\n")

    run_time = np.array([elapsed_time_fileIO,elapsed_time_pyFR])
    np.savez(supereeg_env+"/Total_Run_Time.npz",run_time)

    print(f"Running Full_Mats: lambda={i}")
    start_time_fullmats = time.time()
    run(fullmats_jobsubmit_path, str(i))
    end_time_fullmats = time.time()
    elapsed_time_fullmats = end_time_fullmats - start_time_fullmats
    print(f"Done running Full_mats: lambda={i}")
    print(f"Total run time {elapsed_time_fullmats} sec\n")

    run_time = np.array([elapsed_time_fileIO,elapsed_time_pyFR,elapsed_time_fullmats])
    np.savez(supereeg_env+"/Total_Run_Time.npz",run_time)

    print(f"Running Ave_mats: lambda={i}")
    start_time_avemats = time.time()
    run(avemats_jobsubmit_path)
    end_time_avemats = time.time()
    elapsed_time_avemats = end_time_avemats - start_time_avemats
    print(f"Done running Ave_mats: lambda={i}")
    print(f"Total run time {elapsed_time_avemats} sec\n")

    run_time = np.array([elapsed_time_fileIO,elapsed_time_pyFR,elapsed_time_fullmats,elapsed_time_avemats])
    np.savez(supereeg_env+"/Total_Run_Time.npz",run_time)

    print(f"Running Recon: lambda={i}")
    start_time_recon = time.time()
    run(reacon_jobsubmit_path, str(i))
    end_time_recon = time.time()
    elapsed_time_recon = end_time_recon - start_time_recon
    print(f"Done running Recon: lambda={i}")
    print(f"Total run time {elapsed_time_recon} sec\n")

    run_time = np.array([elapsed_time_fileIO,elapsed_time_pyFR,elapsed_time_fullmats,elapsed_time_avemats,elapsed_time_recon])
    #run_time = np.array([elapsed_time_recon])
    np.savez(supereeg_env+"/Total_Run_Time.npz",run_time)

    new_name = supereeg_env + f"_{i}_test"
    os.rename(supereeg_env, new_name)
    os.mkdir(supereeg_env)