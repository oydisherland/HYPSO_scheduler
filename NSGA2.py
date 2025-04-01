import numpy as np
import random
import math
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from pymoo.operators.survival.rank_and_crowding.metrics import get_crowding_function
from pymoo.mcdm.high_tradeoff import HighTradeoffPoints
from pymoo.visualization.scatter import Scatter
from collections import namedtuple

from ALNS_algorithm import runALNS, createInitialSolution
from get_target_passes import getModelInput
from scheduling_model import SP, OH
from visualize_schedual import printSchedual


INSTANCE = namedtuple("INSTANCE", ["id", "objectiveValues", "schedual"])

def printObjectiveSpace(fronts, objectiveSpace, F_selected):

    pareto_front_indices = fronts[0]
    pareto_front = objectiveSpace[pareto_front_indices]

    print("Pareto Front (Rank 0):")
    print(pareto_front)

    plot = Scatter(title="Pareto Front")
    plot.add(objectiveSpace, color="blue")
    plot.add(pareto_front, facecolor="green")
    plot.add(F_selected, facecolor="none", edgecolor="red")
    plot.show()


def runNSGA(
            popSize: int, 
            nRuns: int,
            ttwList: list, 
            schedulingParameters: SP,  
            oh: OH):
    
    printarray = []
    population = []

    # Create initial induvidual
    initSolution = createInitialSolution(ttwList.copy(), schedulingParameters, oh, destructionRate=0.3, maxSizeTabooBank=20)

    result, _ = runALNS(
        initSolution.otList.copy(),
        initSolution.ttwList.copy(),
        schedulingParameters,  
        oh, 
        destructionRate = round(random.uniform(0.1,0.7),2), 
        maxSizeTabooBank = random.randint(2, 20))
    
    best = result.best_state
    schedual = best.otList
    population.append(INSTANCE(0, best.maxObjective, schedual))


    # Main loop in the NSGA2 algorithm
    for runNr in range(nRuns):
        #### Mutation using ALNS

        iterationNumber = popSize - len(population)
        for i in range(iterationNumber):
            # Create mutation of the induvidual population[i], or create initial population

            if(i >= len(population)):
                # Create initial population
                otList_i = initSolution.otList.copy()
            else:
                # create mutation
                otList_i = population[i].schedual.copy()

            newIndividual, _ = runALNS(
                otList_i,
                ttwList.copy(),
                schedulingParameters, 
                oh, 
                destructionRate = round(random.uniform(0.1,0.7),2), 
                maxSizeTabooBank = random.randint(2, 20))
            
            best = newIndividual.best_state
            schedual = best.otList

            population.append(INSTANCE(len(population) + 1 , best.maxObjective, schedual))
            print("created instance", i)


        #### Selection using non dominated sorting and crowding distance

        # Find the maximum objective values in the population
        # maxPriority = max([ind.objectiveValues[0] for ind in population])
        # minPriority = min([ind.objectiveValues[0] for ind in population])
        # diffPriority = maxPriority - minPriority
        # maxImageQuality = max([ind.objectiveValues[1] for ind in population])
        # minImageQuality = min([ind.objectiveValues[1] for ind in population])
        # diffImageQuality = maxImageQuality - minImageQuality

        # Represent population in objective space scaled from 1 to 100
        objectiveSpace = np.empty((0, 2))
        for induvidual in population:

            priority = induvidual.objectiveValues[0]
            imageQuality = induvidual.objectiveValues[1]
            
            # #scale objectiveVal priority
            # priority = 100 * ( (priority - minPriority) / diffPriority )

            #nonlinear scaling of imageQuality
            # imageQuality = math.sin( ((imageQuality-minImageQuality) / diffImageQuality) * (math.pi/2) ) * 100
            imageQuality = ( 1 - math.cos(math.radians(imageQuality)) ) * 100

            objectiveSpace = np.vstack([objectiveSpace, [priority, imageQuality]])
        objectiveSpace_minimization = -objectiveSpace

        # Perform non-dominated sorting and extract the fronts from objective space
        nds = NonDominatedSorting()
        fronts = nds.do(objectiveSpace_minimization, n_stop_if_ranked=10) # not sure what n_stop_if_ranked do!

        target = popSize // 2 
        selected_indices = []

        # Select top 50% of induviduals in population
        for front in fronts:

            if len(selected_indices) + len(front) <= target:
                ### Add the entire front to the selected solutions

                selected_indices.extend(front)
            else:
                ### Select the best solutions in current front based on crowding distance
                
                n_select = target - len(selected_indices)

                # Calculate crowding distance for the current front
                crowding_function = get_crowding_function('cd')
                crowding_distances = crowding_function.do(F=objectiveSpace[front], n_remove=1)

                # Sort the indicies of the front based on crowding distance
                front_with_crowding = list(zip(front, crowding_distances))
                front_with_crowding.sort(key=lambda x: x[1], reverse=True)

                selected_indices.extend([x[0] for x in front_with_crowding[:n_select]])
                break

        F_selected = objectiveSpace[selected_indices]
        newPopulation = []
        for index in selected_indices:
            newPopulation.append(population[index])

        population = newPopulation

        #### Printing results: 
        print(f"Population size: {len(population)}, and {len(newPopulation)} added round {runNr}")
        
        printarray.append((fronts, objectiveSpace, F_selected))
    #end main loop
    print("Fronts:", fronts)
    print("Pareto front indices (fronts[0]):", fronts[0])
    #Here I need a function to choose the best solution from the last population
    fronts, objectiveSpace, F_selected = printarray[-1]
    pareto_front_indices = fronts[0]
    pareto_front = objectiveSpace[pareto_front_indices]
    print("Pareto front:", pareto_front, "shape[0] = ", pareto_front.shape[0], "shape[1] = ", pareto_front.shape[1])
    bestIndex = 0
    if pareto_front.shape[1] == 0:
        raise ValueError("No solutions found")
    elif pareto_front.shape[1] == 1:
        best_F = pareto_front[0]
    else:
        selector = HighTradeoffPoints()
        selected = selector.do(pareto_front, n_points=1)
        best_F = pareto_front[selected[0]]
        bestIndex = selected[0]

    return printarray, best_F, bestIndex, population


popSize = 20
instances = []
schedulingParameters = SP(20, 60, 90)
oh, ttwList = getModelInput(50, 2, 2, 1)

printArray, best_F, bestIndex, population = runNSGA(popSize, 4, ttwList, schedulingParameters, oh)
i = 1
# for element in printArray:
#     fronts, objectiveSpace, F_selected = element
#     print(f" From round{i}: {objectiveSpace[fronts[0]]}")
#     # printObjectiveSpace(fronts, objectiveSpace, F_selected)
#     i += 1 
fronts, objectiveSpace, F_selected = printArray[-1]
print(f"Best solution: {best_F}")
printObjectiveSpace(fronts, objectiveSpace, F_selected)
printSchedual(population[bestIndex].schedual)

 