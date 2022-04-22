#!/bin/bash
#SBATCH --tasks-per-node 1
#SBATCH --cpus-per-task 1
#SBATCH --nodes 1
#SBATCH --time 01:00:00
#SBATCH --job-name sigopt_gmx
#SBATCH --partition gpu
#SBATCH --gres=gpu:1

module use /home/exacloud/software/modules/

module purge
module load openmpi/3.1.6
module load gromacs/2020.2+cuda

N_WORKERS=4

sigopt create experiment

# Make workers
for i in `seq 0 $N_WORKERS`; do

    echo "Starting worker $i"

    mkdir -p worker_$i
    ln -s ../experiment.yml experiment.yml
    ln -s ../step5_1.tpr step5_1.tpr
    ln -s ../sigoptimize_parallel.py sigoptimize_parallel.py

    cd worker_$i
    sigopt start-worker 1234 python sigoptimize_parallel.py &

    cd ..

done