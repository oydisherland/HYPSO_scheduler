import numpy as np
import math
import matplotlib.pyplot as plt
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from pymoo.operators.survival.rank_and_crowding.metrics import get_crowding_function
from pymoo.mcdm.high_tradeoff import HighTradeoffPoints
from collections import namedtuple

from algorithm.ALNS_algorithm import runALNS, createInitialSolution
from scheduling_model import SP, OH, GSTW
from transmission_scheduling.input_parameters import TransmissionParams

INDIVIDUAL = namedtuple("INDIVIDUAL", ["id", "objectiveValues", "schedule", "ttwList"])

def findKneePoint(fronts, objectiveSpace):
        """ Finds the knee point in the Pareto front using the HighTradeoffPoints method
        Output:
        - bestSolution: the objective values of the best solution found
        - bestIndex: the index of the best solution in the final population
        """
        pareto_front_indices = fronts[0]
        pareto_front = objectiveSpace[pareto_front_indices]

        if pareto_front.shape[0] == 0:
            # Should not happen, means no solution in objective space
            raise ValueError("No solutions found")
        elif pareto_front.shape[0] == 1:
            bestSolution = pareto_front[0]
            bestIndex = pareto_front_indices[0]
        elif pareto_front.shape[0] == 2:
            # Select the solution with the highest priority and image quality
            bestFrontIndex = np.argmax(pareto_front[:, 0])
            bestSolution = pareto_front[bestFrontIndex]
            bestIndex = pareto_front_indices[bestFrontIndex]
        else:
            selector = HighTradeoffPoints()
            selected = selector.do(pareto_front, n_points=1)
            bestSolution = pareto_front[selected[0]]
            bestIndex = pareto_front_indices[selected[0]]

        return bestSolution, bestIndex

def runNSGA(
            populationSize: int, 
            nsga2Runs: int,
            ttwList: list,
            gstwList: list[GSTW],
            schedulingParameters: SP,
            transmissionParameters: TransmissionParams,
            oh: OH,
            alnsRuns: int,
            isTabooBankFIFO: bool,
            IQNonLinear: bool,
            destructionNumber: int,
            maxSizeTabooBank: int,
            optimalTermination: bool=False):
    
    """ Runs the NSGA2 algorithm to optimize the observation schedule
    Output:
    - bestSchedule: the schedule of the best solution found
    - iterationData: list with data from each iteration (fronts, objectiveSpace, selectedobjective values)
    - bestSolution: the objective values of the best solution found
    - bestIndex: the index of the best solution in the final population
    - oldPopulation: the final population of solutions
    """

    iterationData = []
    population = []

    previousParetoFront = []
    terminationCounter = 0

    print(f"NSGA2 main loop using total of {nsga2Runs} runs: ", end='', flush=True)
    ##### Main loop in the NSGA2 algorithm
    for generation in range(nsga2Runs):
        #### Creating offsprings using ALNS

        nrOfOffsprings = populationSize - len(population)
        for i in range(nrOfOffsprings):
            # Create mutation of the individual population[i], or create initial population

            if i >= len(population):
                # Create initial population
                otList_i = createInitialSolution(ttwList.copy(), gstwList, schedulingParameters, transmissionParameters,
                                         oh, destructionNumber, maxSizeTabooBank, isTabooBankFIFO).otList
            else:
                # create mutation
                otList_i = population[i].schedule.copy()

            newIndividual, _ = runALNS(
                otList_i,
                ttwList.copy(),
                gstwList,
                schedulingParameters,
                transmissionParameters,
                oh,
                destructionNumber,
                maxSizeTabooBank,
                alnsRuns,
                isTabooBankFIFO)
            
            best = newIndividual.best_state
            schedule = best.otList
            population.append(INDIVIDUAL(len(population) , best.maxObjective, schedule, best.ttwList.copy()))


        #### Selection using non dominated sorting and crowding distance

        # Represent population in objective space scaled from 1 to 100
        objectiveSpace = np.empty((0, 2))
        for individual in population:

            priority = individual.objectiveValues[0]
            imageQuality = individual.objectiveValues[1]
            
           
            if IQNonLinear:
                imageQuality = ( 1 - math.cos(math.radians(imageQuality)) ) * 100

            objectiveSpace = np.vstack([objectiveSpace, [priority, imageQuality]])
        objectiveSpace_minimization = -objectiveSpace

        # Perform non-dominated sorting and extract the fronts from objective space
        nds = NonDominatedSorting()
        fronts = nds.do(objectiveSpace_minimization, n_stop_if_ranked=None)

        reducedPopulationSize = populationSize // 2
        selected_indices = []

        #### Select top 50% of individuals in population and store their index in selected_indices
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

                # Sort the indices of the front based on crowding distance
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
        if not optimalTermination:
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
        bestSchedule = oldPopulation[bestIndex].schedule
    except IndexError:
        print(f"IndexError: bestIndex {bestIndex} and population size {len(oldPopulation)}")
        bestSchedule = None

    return bestSchedule, iterationData, bestSolution, bestIndex, oldPopulation
