#!/bin/bash
#SBATCH --ntasks 20
#SBATCH --cpus-per-task 1
#SBATCH --time 01:00:00
#SBATCH --job-name sigopt_gmx
#SBATCH --partition exacloud

module use /home/exacloud/software/modules/

module purge
module load openmpi/3.1.6
module load gromacs/2020.2+cuda

# CPUS-per-task should match this
N_WORKERS=$(grep "parallel" experiment.yml | cut -d ' ' -f 2)

echo "Creating sigopt experiment"

EXP_OUT=$(sigopt create experiment)
echo $EXP_OUT
EXP_ID=$(echo $EXP_OUT | grep -m 1 -o -P '(start-worker \d+)' | cut -d ' ' -f 2)

echo "Experiment ${EXP_ID} launched"

# Make workers
for i in `seq 0 $N_WORKERS`; do

    echo "Starting worker $i"

    rm -r worker_$i
    mkdir -p worker_$i

    cd worker_$i

    ln -s ../experiment.yml experiment.yml
    ln -s ../step5_1.tpr step5_1.tpr
    ln -s ../sigoptimize_parallel.py sigoptimize_parallel.py

    SIGOPT_CMD="srun --exact -N 1 -n 1 -c 1 --job-name worker$i sigopt start-worker ${EXP_ID} python sigoptimize_parallel.py"
    echo "Attempting worker start with $SIGOPT_CMD"
    $SIGOPT_CMD &
    echo "Finished attempt"

    cd ..

done

wait
