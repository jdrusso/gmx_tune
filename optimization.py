import sigopt
import gromacs

# Define SLURM runner
import gromacs.run
class MDrunnerSLURM(gromacs.run.MDrunner):
    """Manage running :program:`mdrun` as an MPI multiprocessor job.

       `MDrunnerSLURM.run()` takes optional kwargs which are passed to srun.
    """

    mdrun = "gmx_mpi mdrun"
    mpiexec = "/usr/bin/srun"


# Do a single gromacs run, with specified parameters
def do_gromacs_run(
    mdrun_args,
    slurm_args={},
    slurm=False
):
    
    mdrun_args = {}
    slurm_args = {}
    
    if slurm:
        runner = MDrunnerSLURM()
    else:
        runner = gromacs.run.MDrunner()

    runner.run(mdrunargs=mdrun_args, **slurm_args)


# TODO: Sigopt loop


### Slurm Args

# CPUS
slurm_args = {'mpi':'pmi2'}
n_ranks = 3
n_omp = 2

# GPUS
n_gpus = 1

slurm_args['gres'] = f'gpu:{n_gpus}'
slurm_args['n'] = n_ranks

### MDRun Args
mdrun_args = {'v':'yes', 'deffnm':'step5_1'}
mdrun_args['ntomp'] = n_omp


if __name__ == '__main__':

   runner = gromacs.run.MDrunner()

   # runner = MDrunnerSLURM()
   runner.run(mdrunargs=mdrun_args)
