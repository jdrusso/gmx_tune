# Note: you must load the gromacs module before running (even if the arch on the login node wouldn't let you actually execute it)

import sigopt
import gromacs
import subprocess
from subprocess import PIPE
from datetime import timedelta

# Define SLURM runner
import gromacs.run
class MDrunnerSLURM(gromacs.run.MDrunner):
    """Manage running :program:`mdrun` as an MPI multiprocessor job.

       `MDrunnerSLURM.run()` takes optional kwargs which are passed to srun.
    """

    mdrun = "gmx_mpi mdrun"
    mpiexec = "/usr/bin/salloc"

    def prehook(self, **kwargs):
        """Launch local smpd."""
        cmds = [['bash', '-c', 'module purge'], 
                ['bash', '-c', 'module use /home/exacloud/software/modules/'], 
                ['bash', '-c', 'module load openmpi/3.1.6'],
                ['bash', '-c', 'module load gromacs/2020.2+cuda'] ]
        for cmd in cmds:
            rc = subprocess.call(cmd)
        return rc

    def mpicommand(self, *args, **kwargs):
        """Return a list of the mpi command portion of the commandline.

        Only allows primitive mpi at the moment:
           *mpiexec* -n *ncores* *mdrun* *mdrun-args*

        (This is a primitive example for OpenMP. Override it for more
        complicated cases.)
        """
        if self.mpiexec is None:
            raise NotImplementedError("Override mpiexec to enable the simple OpenMP launcher")
        # example implementation
        #ncores = kwargs.pop('ncores', 8)
        cmd = [self.mpiexec]
        for key, val in kwargs.items():
        
            cmd.extend([key, str(val)])

        cmd.extend(['srun', '--mpi', 'pmi2'])
        return cmd
        #return [self.mpiexec, '-n', str(ncores)]


# Do a single gromacs run, with specified parameters
def do_gromacs_run(
    mdrun_args,
    slurm_args={},
    slurm=False,
):

    print("Initializing runner") 
    if slurm:
        # TODO: Load module files
        runner = MDrunnerSLURM()
    else:
        runner = gromacs.run.MDrunner()

    #print(f"Running with slurm args {slurm_args}")
    print(f"Running: {' '.join(runner.commandline(**slurm_args))}")
    success = runner.run_check(mdrunargs=mdrun_args, **slurm_args)

    if success is False:
        return None

    # Get timing information
    with open(f"{mdrun_args['deffnm']}.log", 'r') as logfile:
        lines = logfile.readlines()
        performance_line = [line for line in lines if 'Performance' in line]

        ns_per_day = performance_line[0].split()[1]
        ns_per_day = float(ns_per_day)

    # Return ns/day
    return ns_per_day

# TODO: Sigopt loop


### Slurm Args
partition='gpu'

# CPUS
slurm_args = {'--job-name': 'gmx test', '--nodes':1}
n_ranks = 4
cpus_per_task = 2
n_omp = 2

# GPUS
n_gpus = 1

slurm_args['--gres'] = f'gpu:{n_gpus}'
slurm_args['--partition'] = partition
slurm_args['-n'] = n_ranks
slurm_args['--cpus-per-task'] = cpus_per_task

### MDRun Args
mdrun_args = {'v':'yes', 'deffnm':'step5_1'}
mdrun_args['ntomp'] = n_omp
#mdrun_args['nt'] = n_ranks


def do_run():

    params = sigopt.params

    print(f"Launching run!")
    print(params)

    run_id = sigopt.get_run_id()

    
    if (sigopt.params['ranks'] + sigopt.params['pme_ranks']) * sigopt.params['cpus_per_rank'] > 44:
        print("Too many requested resources for one node, this configuration is not available")
        sigopt.log_failure()
        return

    if sigopt.params['pme_ranks'] >= sigopt.params['ranks']:
        print("Too many PME ranks for the number of PP ranks.")
        sigopt.log_failure()
        return

    if sigopt.params['pme_ranks'] & sigopt.params['n_gpus'] > 0:
        print("PME ranks not divisible by GPUs.")
        sigopt.log_failure()
        return

    jobname = f"gmx_opt-{run_id}"
    slurm_args['--job-name'] = jobname

    slurm_args['-n'] = sigopt.params['ranks'] + sigopt.params['pme_ranks']
    slurm_args['--cpus-per-task'] = sigopt.params['cpus_per_rank']
    slurm_args['--gres'] = f"gpu:{sigopt.params['n_gpus']}"
    
    mdrun_args['npme'] = sigopt.params['pme_ranks']
    mdrun_args['ntomp'] = sigopt.params['cpus_per_rank']

    ns_per_day = do_gromacs_run(mdrun_args=mdrun_args, slurm_args=slurm_args, slurm=True)

    if ns_per_day is None:
        print(f"Error in run")
        sigopt.log_failure()
        return

    print(f"*** Completed run, with {ns_per_day:.2f} ns/day")

    print(f"Trying to find runtime for job {jobname}")

    time_in_queue = subprocess.run(
        ["sacct", "--name", jobname, "-X", "-o", "Reserved", "-n", "--parsable2"], 
        stdout=PIPE).stdout.decode('utf-8').split()

    
    hours, minutes, seconds = time_in_queue[-1].split(':')
    queuetime = int(hours)*3600 + int(minutes)*60 + int(seconds)
    print(f"*** Queue time was {queuetime} seconds")

    sigopt.log_metric('ns/day', float(ns_per_day))
    sigopt.log_metric('queuetime', queuetime)




if __name__ == '__main__':

    do_run()
