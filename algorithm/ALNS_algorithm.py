from alns import ALNS
from alns.accept import HillClimbing, SimulatedAnnealing
from alns.select import RandomSelect, RouletteWheel
from alns.stop import MaxRuntime, NoImprovement, MaxIterations

import numpy.random as rnd
import copy

from data_preprocessing.objective_functions import objectiveFunctionPriority, objectiveFunctionImageQuality
from scheduling_model import OH, SP, GSTW
from algorithm.operators import repairOperator, destroyOperator, RepairType, DestroyType
from transmission_scheduling.input_parameters import TransmissionParams


class ProblemState:
    def __init__(self, otList, ttwList, gstwList, oh, destructionNumber, schedulingParameters, transmissionParameters,
                 maxSizeTabooBank, isTabooBankFIFO):
        self.otList = otList
        self.ttwList = ttwList
        self.gstwList = gstwList
        self.oh = oh
        self.destructionNumber = destructionNumber
        self.schedulingParameters = schedulingParameters
        self.transmissionParameters = transmissionParameters
        self.tabooBank = []
        self.maxSizeTabooBank = maxSizeTabooBank
        self.isTabooBankFIFO = isTabooBankFIFO
        self.maxObjective = [0, 0]
        self.imageQuality = 0
        self.maxPriority = max(ot.GT.priority for ot in otList)

    def objective(self) -> float:
        sum_priority = 0
        # Assume the max priority score is if the max amount of captures is scheduled with the highest priority found
        maxPrioritySchedule = self.schedulingParameters.maxCaptures * self.maxPriority
        # Assume the max image quality score is if all captures are made exactly on nadir
        imageQualityMax = 90 * self.schedulingParameters.maxCaptures
        for ot in self.otList:
            sum_priority += ot.GT.priority
            #Negating the sum since the alns solves the minimization problem
        objective = sum_priority / maxPrioritySchedule
        objective += self.imageQuality / imageQualityMax
        return -objective

    def get_context(self):
        # TODO implement a method returning a context vector. This is only
        #  needed for some context-aware bandit selectors from MABWiser;
        #  if you do not use those, this default is already sufficient!
        return None

##### Functions to create initial solution as input to algorithm ###

def initial_state(otList: list, ttwList: list, gstwList: list[GSTW], schedulingParameters: SP,
                  transmissionParams: TransmissionParams, oh: OH, destructionNumber: int, maxSizeTabooBank: int,
                  isTabooBankFIFO: bool) -> ProblemState:
    tabooBank = []
    ttwListResorted, otListAdjusted, objectiveValues = repairOperator(
        ttwList, 
        otList,
        gstwList,
        tabooBank, 
        RepairType.RANDOM,
        schedulingParameters,
        transmissionParams,
        oh,
        True)
    
    state = ProblemState(otListAdjusted, ttwListResorted, gstwList, oh, destructionNumber, schedulingParameters,
                         transmissionParams, maxSizeTabooBank, isTabooBankFIFO)
    state.maxObjective = objectiveValues
    return state
def createInitialSolution(ttwList: list, gstwList: list[GSTW], schedulingParameters: SP,
                          transmissionParams: TransmissionParams, oh: OH, destructionNumber: int, maxSizeTabooBank: int,
                          isTabooBankFIFO: bool):
    """ Creates a randomized initial solution for the ALNS algorithm
    Output:
    - init_sol: the initial ProblemState object for the ALNS algorithm
    """
    otListEmpty = []
    init_sol = initial_state(otListEmpty, ttwList, gstwList, schedulingParameters, transmissionParams, oh,
                             destructionNumber, maxSizeTabooBank, isTabooBankFIFO)
    return init_sol

### Helper functions for destroy and repair operators ###

def removeElementsFromTabooBank(current: ProblemState) -> ProblemState:
    # Remove targets from FIFO queue If the queue is full
    while len(current.tabooBank) + current.destructionNumber >= current.maxSizeTabooBank:
        # Remove the oldest target from the queue
        current.tabooBank.pop(0)
    return current
def getDestructionNumber(current: ProblemState) -> int:
    if len(current.tabooBank) + current.destructionNumber >= current.maxSizeTabooBank:
        # No targets can be romoved
        return 0
    elif len(current.tabooBank) >= current.maxSizeTabooBank - current.destructionNumber:
        # Cannot remove as many taregts as destruction dumber says
        return 1
    else: 
        return current.destructionNumber

### Destroy and repair operators ###

def destroyRandom(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # Make sure to (deep)copy the current state before modifying!
    if current.isTabooBankFIFO:
        # Make space in the taboobank for new round of destructions
        current = removeElementsFromTabooBank(current)
        numberOfTargetsToRemove = current.destructionNumber
    else:
        # Adjust destruction number after the size of the taboo bank
        numberOfTargetsToRemove = getDestructionNumber(current)

    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(
        destroyed.otList, 
        destroyed.ttwList,
        numberOfTargetsToRemove, 
        DestroyType.RANDOM,
        destroyed.oh,
        destroyed.schedulingParameters.hypsoNr)
    
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed
def destroyGreedyPriority(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # Make sure to (deep)copy the current state before modifying!
        # Make sure to (deep)copy the current state before modifying!
    if current.isTabooBankFIFO:
        # Make space in the taboobank for new round of destructions
        current = removeElementsFromTabooBank(current)
        numberOfTargetsToRemove = current.destructionNumber
    else:
        # Adjust destruction number after the size of the taboo bank
        numberOfTargetsToRemove = getDestructionNumber(current)

    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(
        destroyed.otList, 
        destroyed.ttwList,
        numberOfTargetsToRemove, 
        DestroyType.GREEDY_P,
        destroyed.oh,
        destroyed.schedulingParameters.hypsoNr)
    
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed
def destroyGreedyImageQuality(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # Make sure to (deep)copy the current state before modifying!
        # Make sure to (deep)copy the current state before modifying!
    if current.isTabooBankFIFO:
        # Make space in the taboobank for new round of destructions
        current = removeElementsFromTabooBank(current)
        numberOfTargetsToRemove = current.destructionNumber
    else:
        # Adjust destruction number after the size of the taboo bank
        numberOfTargetsToRemove = getDestructionNumber(current) 

    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(
        destroyed.otList, 
        destroyed.ttwList,
        numberOfTargetsToRemove, 
        DestroyType.GREEDY_IQ,
        destroyed.oh,
        destroyed.schedulingParameters.hypsoNr)
    
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed
def destroyCongestion(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # Make sure to (deep)copy the current state before modifying!
        # Make sure to (deep)copy the current state before modifying!
    if current.isTabooBankFIFO:
        # Make space in the taboobank for new round of destructions
        current = removeElementsFromTabooBank(current)
        numberOfTargetsToRemove = current.destructionNumber
    else:
        # Adjust destruction number after the size of the taboo bank
        numberOfTargetsToRemove = getDestructionNumber(current)

    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(
        current.otList, 
        current.ttwList,
        numberOfTargetsToRemove, 
        DestroyType.CONGESTION,
        destroyed.oh,
        destroyed.schedulingParameters.hypsoNr)
    
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed

def repairRandom(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    repaired = copy.deepcopy(current) #Do not know if deep copy is nessecary for the repair operator
    repaired.ttwList, repaired.otList, objectiveValues = repairOperator(
        repaired.ttwList, 
        repaired.otList,
        repaired.gstwList,
        repaired.tabooBank, 
        RepairType.RANDOM, 
        repaired.schedulingParameters,
        repaired.transmissionParameters,
        repaired.oh)
    repaired.imageQuality = objectiveValues[1]
    if objectiveValues[0] > repaired.maxObjective[0]:
        repaired.maxObjective[0] = objectiveValues[0]
    if objectiveValues[1] > repaired.maxObjective[1]:
        repaired.maxObjective[1] = objectiveValues[1]
    return repaired
def repairGreedy(current: ProblemState, rng: rnd.Generator) -> ProblemState: 
    repaired = copy.deepcopy(current)
    repaired.ttwList, repaired.otList, objectiveValues = repairOperator(
        repaired.ttwList, 
        repaired.otList,
        repaired.gstwList,
        repaired.tabooBank, 
        RepairType.GREEDY, 
        repaired.schedulingParameters,
        repaired.transmissionParameters,
        repaired.oh)
    
    repaired.imageQuality = objectiveValues[1]
    if objectiveValues[0] > repaired.maxObjective[0]:
        repaired.maxObjective[0] = objectiveValues[0]
    if objectiveValues[1] > repaired.maxObjective[1]:
        repaired.maxObjective[1] = objectiveValues[1]
    return repaired
def repairSmallTW(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    repaired = copy.deepcopy(current)

    repaired.ttwList, repaired.otList, objectiveValues = repairOperator(
        repaired.ttwList, 
        repaired.otList,
        repaired.gstwList,
        repaired.tabooBank, 
        RepairType.SMALL_TW, 
        repaired.schedulingParameters,
        repaired.transmissionParameters,
        repaired.oh)
    
    repaired.imageQuality = objectiveValues[1]
    if objectiveValues[0] > repaired.maxObjective[0]:
        repaired.maxObjective[0] = objectiveValues[0]
    if objectiveValues[1] > repaired.maxObjective[1]:
        repaired.maxObjective[1] = objectiveValues[1]
    return repaired
def repairCongestion(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    repaired = copy.deepcopy(current)

    repaired.ttwList, repaired.otList, objectiveValues = repairOperator(
        repaired.ttwList, 
        repaired.otList,
        repaired.gstwList,
        repaired.tabooBank, 
        RepairType.CONGESTION, 
        repaired.schedulingParameters,
        repaired.transmissionParameters,
        repaired.oh)
    
    repaired.imageQuality = objectiveValues[1]
    if objectiveValues[0] > repaired.maxObjective[0]:
        repaired.maxObjective[0] = objectiveValues[0]
    if objectiveValues[1] > repaired.maxObjective[1]:
        repaired.maxObjective[1] = objectiveValues[1]
    return repaired

### Function to run ALNS algorithm

def runALNS(initial_otList: list, initial_ttwList: list, gstwList: list[GSTW], schedulingParameters: SP,
            transmissionParameters: TransmissionParams, oh: OH, destructionNumber: int, maxSizeTabooBank: int,
            maxItr: int, isTabooBankFIFO: bool):
    """ Runs the ALNS algorithm to find a good heuristic solution
    Output:
    - result: the result object from the ALNS run, containing the best solution found
    - state: the final ProblemState object of the problem after the ALNS run
    """
    # Format the problem state
    state = ProblemState(initial_otList, initial_ttwList, gstwList, oh, destructionNumber, schedulingParameters,
                         transmissionParameters, maxSizeTabooBank, isTabooBankFIFO)
    state.maxObjective = [objectiveFunctionPriority(initial_otList),
                           objectiveFunctionImageQuality(initial_otList, oh, schedulingParameters.hypsoNr)]

    # Create ALNS and add one or more destroy and repair operators
    alns = ALNS() # Initialize without a random seed
    alns.add_destroy_operator(destroyRandom)
    alns.add_destroy_operator(destroyGreedyPriority)
    # alns.add_destroy_operator(destroyGreedyImageQuality)
    alns.add_destroy_operator(destroyCongestion)
    alns.add_repair_operator(repairRandom)
    alns.add_repair_operator(repairGreedy)
    alns.add_repair_operator(repairSmallTW)
    alns.add_repair_operator(repairCongestion)
   
    # Configure ALNS
    select = RouletteWheel(scores=[5, 2, 1, 0.5], decay=0.8, num_destroy=3, num_repair=4) # initialize with equal operator weights
    # Start configuration
    #accept = SimulatedAnnealing(start_temperature=100, end_temperature=1, step=0.99) 
    # Moderate
    #accept = SimulatedAnnealing(start_temperature=500, end_temperature=1, step=0.99)
    # Agressive (fast cooling)
    accept = SimulatedAnnealing(start_temperature=0.05, end_temperature=0.0025, step=0.9)
    # High Exploration
    #accept = SimulatedAnnealing(start_temperature=2000, end_temperature=0.01, step=0.998)
    # Quick Convergence
    #accept = SimulatedAnnealing(start_temperature=200, end_temperature=10, step=0.90)
    stop = MaxIterations(maxItr)  

    # Run the ALNS algorithm
    result = alns.iterate(state, select, accept, stop)

    # Retrieve the final solution
    # best = result.best_state
    # print(f"Best heuristic solution objective is {best.maxObjective[0]} and {best.maxObjective[1]}.")
    # result.plot_objectives()
    # plt.show()
    # print()
    return result, state



