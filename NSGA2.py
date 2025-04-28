import numpy as np
import random
import math
import csv
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
    previousParetoFront = []
    terminationCounter = 0
    # Main loop in the NSGA2 algorithm
    for runNr in range(nRuns):
        #### Creating offsprings using ALNS

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

        reducedPopSize = popSize // 2 
        selected_indices = []

        # Select top 50% of induviduals in population
        for front in fronts:

            if len(selected_indices) + len(front) <= reducedPopSize:
                ### Add the entire front to the selected solutions

                selected_indices.extend(front)
            else:
                ### Select the best solutions in current front based on crowding distance
                
                n_select = reducedPopSize - len(selected_indices)

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

        # Check termination criteria
        if runNr > 0:
            # Check if the Pareto front has not changed
            result = np.isin(previousParetoFront, fronts[0])

            if np.all(result):
                if terminationCounter < 2:
                    # pareto front is the same as previous, increase termination counter
                    terminationCounter += 1
                elif terminationCounter == 2:
                    # pareto front has not changed for 2 iterations, stop the algorithm
                    print(f"Termination criteria met at run {runNr}, break loop with {nRuns - runNr} iterations left")
                    break
            else:
                #if pareto front has changed, reset termination counter
                terminationCounter = 0
            
        previousParetoFront = fronts[0]

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
    elif pareto_front.shape[1] == 2:
        # Select the solution with the highest priority and image quality
        best_F = pareto_front[np.argmax(pareto_front[:, 0])]
        bestIndex = np.argmax(pareto_front[:, 0])
    else:
        selector = HighTradeoffPoints()
        selected = selector.do(pareto_front, n_points=1)
        best_F = pareto_front[selected[0]]
        bestIndex = selected[0]

    return printarray, best_F, bestIndex, population


popSize = 20
instances = []
schedulingParameters = SP(20, 60, 90)
startTime = "2025-04-01 16:47:49.990785"
oh, ttwList = getModelInput(50, 2, 2, 1, startTime)

printArray, best_F, bestIndex, population = runNSGA(popSize, 2, ttwList, schedulingParameters, oh)
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


# Save population[bestIndex].schedual to optimizedSchedual.csv
optimized_schedual_file = "optimizedSchedual.csv"
with open(optimized_schedual_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Task", "Start Time", "End Time"])  # Example header, adjust as needed
    for row in population[bestIndex].schedual:
        writer.writerow(row)

print(f"Optimized schedule saved to {optimized_schedual_file}")

# Save fronts, objectiveSpace, and F_selected to finalPopulationData.csv
final_population_data_file = "finalPopulationData.csv"
with open(final_population_data_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Fronts"])  # Header for fronts
    for front in fronts:
        writer.writerow(front)


 