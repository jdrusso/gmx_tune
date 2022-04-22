import sigopt
import gromacs
import subprocess

# Define SLURM runner
import gromacs.run
class MDrunnerSLURM(gromacs.run.MDrunner):
    """Manage running :program:`mdrun` as an MPI multiprocessor job.

       `MDrunnerSLURM.run()` takes optional kwargs which are passed to srun.
    """

    mdrun = "gmx_mpi mdrun"
    mpiexec = "/usr/bin/srun"

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
        return cmd
        #return [self.mpiexec, '-n', str(ncores)]


# Do a single gromacs run, with specified parameters
def do_gromacs_run(
    mdrun_args,
    slurm_args={},
    slurm=False,
):
 
    if slurm:
        # TODO: Load module files
        runner = MDrunnerSLURM()
    else:
        runner = gromacs.run.MDrunner()

    #print(f"Running with slurm args {slurm_args}")
    print(f"Running: {' '.join(runner.commandline(**slurm_args))}")
    runner.run(mdrunargs=mdrun_args, **slurm_args)

    

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
slurm_args = {'--mpi':'pmi2', '--job-name': 'gmx test'}
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


if __name__ == '__main__':

    # TODO: Add some of the categorical parameters -- pinning, PME on CPU/GPU, etc
    # TODO: Also could minimize resource wait time as another metric.... At least store it
    #           I can access this with `sacct -j <jobid> -X -n --parsable2 -o Reserved`, I just
    #           need a way to get job IDs.
    # TODO: Store node info for a run
    # TODO: Maybe I can use conditional parameters the way I wanted to use integer linear constraints
    experiment = sigopt.create_experiment(
        name='GMX parameter tune',
        budget=30,
        parameters = [
            {"name":"cpus_per_task", "type":"int", "bounds":{"min":1, "max":4}},
            {"name":"ranks", "type":"int", "bounds":{"min":1, "max":10}},
            {"name":"n_gpus", "type":"int", "grid":[1,2,3]},
            #dict(name='npme', type='int', bounds={'min':1, 'max':4}),
        ],
        metrics = [{"name": "ns/day", "strategy": "optimize", "objective": "maximize"}],
        metadata = {'n_gpus':n_gpus, 'partition':partition},
    )

    for run in experiment.loop():
        with run:

            print(f"Launching run {run.id}!")
            print(run.params)

            slurm_args['-n'] = run.params['ranks'] + run.params['npme']
            slurm_args['--cpus-per-task'] = run.params['cpus_per_task']
            slurm_args['--gres'] = f"gpu:{run.params['n_gpus']}"
            
            #mdrun_args['npme'] = run.params['npme']
            mdrun_args['ntomp'] = run.params['cpus_per_task']

            ns_per_day = do_gromacs_run(mdrun_args=mdrun_args, slurm_args=slurm_args, slurm=True)
            print(f"*** Completed run, with {ns_per_day:.2f} ns/day")

            run.log_metric('ns/day', float(ns_per_day))
