from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
import numpy as np
from pymoo.visualization.scatter import Scatter
from collections import namedtuple

from ALNS_algorithm import runALNS
from get_target_passes import getModelInput
from scheduling_model import SP, OH
import random



popSize = 10

INSTANCE = namedtuple("INSTANCE", ["id", "objectiveValues", "schedual"])

instances = []
schedulingParameters = SP(20, 60, 90)
oh, ttwList = getModelInput(50, 2, 2, 1)

for i in range(popSize):

    result, init_sol = runALNS(schedulingParameters, ttwList.copy(), oh, destructionRate = round(random.uniform(0.1,0.7),2), maxSizeTabooBank = random.randint(2, 20))
    best = result.best_state
    schedual = best.otList

    instances.append(INSTANCE(i, best.maxObjective, schedual))
    print("created instance", i)


# Assume F is an array of objective values (rows = solutions, cols = objectives)

F = np.empty((0, 2))
for inst in instances:
    F = np.vstack([F, inst.objectiveValues])

# Perform non-dominated sorting
fronts = NonDominatedSorting().do(F, only_non_dominated_front=True)

# Extract Pareto front
pareto_front = F[fronts]

print("Pareto Front:")
print(pareto_front)

pareto_instances = [instances[i] for i in fronts]
# print("Pareto Instances:", pareto_instances.index) 

plot = Scatter(title="Pareto Front")
plot.add(F, color="blue")
plot.add(pareto_front, facecolor="none", edgecolor="red")
plot.show()