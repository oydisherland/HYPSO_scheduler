import numpy as np
import math
import matplotlib.pyplot as plt
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from pymoo.operators.survival.rank_and_crowding.metrics import get_crowding_function
from pymoo.mcdm.high_tradeoff import HighTradeoffPoints
from pymoo.visualization.scatter import Scatter
from collections import namedtuple

from algorithm.ALNS_algorithm import runALNS, createInitialSolution
from scheduling_model import SP, OH


INDIVIDUAL = namedtuple("INDIVIDUAL", ["id", "objectiveValues", "schedule", "ttwList"])

def findKneePoint(fronts, objectiveSpace):
        pareto_front_indices = fronts[0]
        pareto_front = objectiveSpace[pareto_front_indices]
        bestIndex = 0
        if pareto_front.shape[1] == 0:
            # Should not happen, means no solution in objective space
            raise ValueError("No solutions found")
        elif pareto_front.shape[1] == 1:
            bestSolution = pareto_front[0]
        elif pareto_front.shape[1] == 2:
            # Select the solution with the highest priority and image quality
            bestSolution = pareto_front[np.argmax(pareto_front[:, 0])]
            bestIndex = np.argmax(pareto_front[:, 0])
        else:
            selector = HighTradeoffPoints()
            selected = selector.do(pareto_front, n_points=1)
            bestSolution = pareto_front[selected[0]]
            bestIndex = selected[0]
        
        return bestSolution, bestIndex

def runNSGA(
            populationSize: int, 
            nsga2Runs: int,
            ttwList: list, 
            schedulingParameters: SP,  
            oh: OH,
            alnsRuns: int,
            isTabooBankFIFO: bool,
            IQNonLinear: bool,
            destructionNumber: int,
            maxSizeTabooBank: int,
            optimalTermination: bool=False):
    
    iterationData = []
    population = []

    #### Create initial induvidual
    initSolution = createInitialSolution(ttwList.copy(), schedulingParameters, oh, destructionNumber, maxSizeTabooBank, isTabooBankFIFO)

    result, _ = runALNS(
        initSolution.otList.copy(),
        initSolution.ttwList.copy(),
        schedulingParameters,  
        oh, 
        destructionNumber, 
        maxSizeTabooBank,
        alnsRuns,
        isTabooBankFIFO)
    
    best = result.best_state
    schedule = best.otList
    population.append(INDIVIDUAL(0, best.maxObjective, schedule, best.ttwList.copy()))
    previousParetoFront = []
    terminationCounter = 0

    print(f"NSGA2 main loop using total of {nsga2Runs} runs: ", end='', flush=True)
    ##### Main loop in the NSGA2 algorithm
    for generation in range(nsga2Runs):
        #### Creating offsprings using ALNS

        nrOfOffsprings = populationSize - len(population)
        for i in range(nrOfOffsprings):
            # Create mutation of the induvidual population[i], or create initial population

            if(i >= len(population)):
                # Create initial population
                otList_i = initSolution.otList.copy()
            else:
                # create mutation
                otList_i = population[i].schedule.copy()

            newIndividual, _ = runALNS(
                otList_i,
                ttwList.copy(),
                schedulingParameters, 
                oh, 
                destructionNumber, 
                maxSizeTabooBank,
                alnsRuns,
                isTabooBankFIFO)
            
            best = newIndividual.best_state
            schedule = best.otList
            population.append(INDIVIDUAL(len(population) + 1 , best.maxObjective, schedule, best.ttwList.copy()))


        #### Selection using non dominated sorting and crowding distance

        # Represent population in objective space scaled from 1 to 100
        objectiveSpace = np.empty((0, 2))
        for induvidual in population:

            priority = induvidual.objectiveValues[0]
            imageQuality = induvidual.objectiveValues[1]
            
           
            if IQNonLinear:
                imageQuality = ( 1 - math.cos(math.radians(imageQuality)) ) * 100

            objectiveSpace = np.vstack([objectiveSpace, [priority, imageQuality]])
        objectiveSpace_minimization = -objectiveSpace

        # Perform non-dominated sorting and extract the fronts from objective space
        nds = NonDominatedSorting()
        fronts = nds.do(objectiveSpace_minimization, n_stop_if_ranked=None)

        reducedPopulationSize = populationSize // 2
        selected_indices = []

        #### Select top 50% of induviduals in population and store their index in selected_indices
        for front in fronts:

            if len(selected_indices) + len(front) <= reducedPopulationSize:
                ### Add the entire front to the selected solutions

                selected_indices.extend(front)
            else:
                ### Select the best solutions in current front based on crowding distance
                n_select = reducedPopulationSize - len(selected_indices)

                # Calculate crowding distance for the current front
                crowding_function = get_crowding_function('cd')
                crowding_distances = crowding_function.do(F=objectiveSpace[front], n_remove=1)

                # Sort the indicies of the front based on crowding distance
                front_with_crowding = list(zip(front, crowding_distances))
                front_with_crowding.sort(key=lambda x: x[1], reverse=True)

                selected_indices.extend([x[0] for x in front_with_crowding[:n_select]])
                break
        
        ### Store the objective values of the selected solutions in selectedObjectiveVals
        selectedObjectiveVals = objectiveSpace[selected_indices]
        newPopulation = []
        for index in selected_indices:
            newPopulation.append(population[index])

        oldPopulation = population.copy()
        population = newPopulation

        #### Printing results: 
        print(f"{generation + 1} | ", end='', flush=True)

        ### Save all data from this iteration in iterationData, to use for analysis of the algorithm
        iterationData.append((fronts, objectiveSpace, selectedObjectiveVals))

        #### Check termination criteria
        if optimalTermination == False:
            ### Termination criteria: continue iterations for nsga2Runs, main loop ends here
            continue
    
        ### Termination criteria: stop algorithm if pareto front has not changed for 2 iterations
        if generation > 0:
            # Check if the Pareto front has not changed
            result = np.isin(previousParetoFront, fronts[0])

            if np.all(result):
                if terminationCounter < 2:
                    # pareto front is the same as previous, increase termination counter
                    terminationCounter += 1
                elif terminationCounter == 2:
                    # pareto front has not changed for 2 iterations, stop the algorithm
                    print(f"Termination criteria met at run {generation}, break loop with {nsga2Runs - generation} iterations left")
                    break
            else:
                # if pareto front has changed, reset termination counter
                terminationCounter = 0  

        previousParetoFront = fronts[0]

    ##### end main loop

    bestSolution, bestIndex = findKneePoint(fronts, objectiveSpace)
    try:
        bestSchedule = population[bestIndex].schedule
    except IndexError:
        print(f"IndexError: bestIndex {bestIndex} and population size {len(population)}")
        bestSchedule = None

    return bestSchedule, iterationData, bestSolution, bestIndex, oldPopulation
