from alns import ALNS
from alns.accept import HillClimbing
from alns.select import RandomSelect
from alns.stop import MaxRuntime

import numpy.random as rnd


class ProblemState:
    # TODO add attributes that encode a solution to the problem instance

    def objective(self) -> float:
        # TODO implement the objective function
        pass

    def get_context(self):
        # TODO implement a method returning a context vector. This is only
        #  needed for some context-aware bandit selectors from MABWiser;
        #  if you do not use those, this default is already sufficient!
        return None


def initial_state() -> ProblemState:
    # TODO implement a function that returns an initial solution
    pass


def destroy(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # TODO implement how to destroy the current state, and return the destroyed
    #  state. Make sure to (deep)copy the current state before modifying!
    pass


def repair(destroyed: ProblemState, rng: rnd.Generator) -> ProblemState:
    # TODO implement how to repair a destroyed state, and return it
    pass


# Create the initial solution
init_sol = initial_state()
print(f"Initial solution objective is {init_sol.objective()}.")

# Create ALNS and add one or more destroy and repair operators
alns = ALNS(rnd.default_rng(seed=42))
alns.add_destroy_operator(destroy)
alns.add_repair_operator(repair)

# Configure ALNS
select = RandomSelect(num_destroy=1, num_repair=1)  # see alns.select for others
accept = HillClimbing()  # see alns.accept for others
stop = MaxRuntime(60)  # 60 seconds; see alns.stop for others

# Run the ALNS algorithm
result = alns.iterate(init_sol, select, accept, stop)

# Retrieve the final solution
best = result.best_state
print(f"Best heuristic solution objective is {best.objective()}.")