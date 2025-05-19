from alns import ALNS
from alns.accept import HillClimbing, SimulatedAnnealing
from alns.select import RandomSelect
from alns.stop import MaxRuntime, NoImprovement, MaxIterations

import numpy.random as rnd
import copy
import matplotlib.pyplot as plt

from scheduling_model import OH ,SP
from operators import repairOperator, destroyOperator, RepairType, DestroyType

class ProblemState:
    def __init__(self, otList, ttwList, oh, destructionNumber, schedulingParameters, maxSizeTabooBank, isTabooBankFIFO):
        self.otList = otList
        self.ttwList = ttwList
        self.oh = oh
        self.destructionNumber = destructionNumber
        self.schedulingParameters = schedulingParameters
        self.tabooBank = []
        self.maxSizeTabooBank = maxSizeTabooBank
        self.isTabooBankFIFO = isTabooBankFIFO
        self.maxObjective = [0, 0]
        self.imageQuality = 0

    def objective(self) -> float:
        sum_priority = 0
        priotityMax = 12454
        for ot in self.otList:
            sum_priority += ot.GT.priority
            #Negating the sum since the alns solves the minimization problem
        sum = 100 * (sum_priority / priotityMax)
        sum += self.imageQuality
        return -sum

    def get_context(self):
        # TODO implement a method returning a context vector. This is only
        #  needed for some context-aware bandit selectors from MABWiser;
        #  if you do not use those, this default is already sufficient!
        return None


def initial_state(otList: list, ttwList: list, schedulingParameters: SP, oh: OH, destructionNumber: int, maxSizeTabooBank: int, isTabooBankFIFO: bool) -> ProblemState:
    tabooBank = []
    ttwListResorted, otList, objectiveValues = repairOperator(
        ttwList, 
        otList, 
        tabooBank, 
        RepairType.RANDOM, 
        schedulingParameters, 
        oh)
    
    state = ProblemState(otList, ttwListResorted, oh, destructionNumber, schedulingParameters, maxSizeTabooBank, isTabooBankFIFO)
    state.maxObjective = objectiveValues
    return state

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
        destroyed.oh)
    
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
        destroyed.oh)
    
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
        destroyed.oh)
    
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
        destroyed.oh)
    
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed


def repairRandom(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    repaired = copy.deepcopy(current) #Do not know if deep copy is nessecary for the repair operator
    repaired.ttwList, repaired.otList, objectiveValues = repairOperator(
        repaired.ttwList, 
        repaired.otList, 
        repaired.tabooBank, 
        RepairType.RANDOM, 
        repaired.schedulingParameters, 
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
        repaired.tabooBank, 
        RepairType.GREEDY, 
        repaired.schedulingParameters, 
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
        repaired.tabooBank, 
        RepairType.SMALL_TW, 
        repaired.schedulingParameters, 
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
        repaired.tabooBank, 
        RepairType.CONGESTION, 
        repaired.schedulingParameters, 
        repaired.oh)
    
    repaired.imageQuality = objectiveValues[1]
    if objectiveValues[0] > repaired.maxObjective[0]:
        repaired.maxObjective[0] = objectiveValues[0]
    if objectiveValues[1] > repaired.maxObjective[1]:
        repaired.maxObjective[1] = objectiveValues[1]
    return repaired


def createInitialSolution(ttwList: list, schedulingParameters: SP, oh: OH, destructionNumber: int, maxSizeTabooBank: int, isTabooBankFIFO: bool):
    
    # Create the initial solution
    otListEmpty = []
    init_sol = initial_state(otListEmpty, ttwList, schedulingParameters, oh, destructionNumber, maxSizeTabooBank, isTabooBankFIFO)
    
    return init_sol

# Function to run ALNS algorithm
def runALNS( inital_otList: list, initial_ttwList: list, schedulingParameters: SP, oh: OH, destructionNumber: int, maxSizeTabooBank: int, maxItr: int, isTabooBankFIFO: bool):
    
    # Format the problem state
    state = ProblemState(inital_otList, initial_ttwList, oh, destructionNumber, schedulingParameters, maxSizeTabooBank, isTabooBankFIFO)
    state.maxObjective = [0,0]

    # Create ALNS and add one or more destroy and repair operators
    alns = ALNS.ALNS() # ALNS() # Initialize without a random seed
    alns.add_destroy_operator(destroyRandom)
    alns.add_destroy_operator(destroyGreedyPriority)
    # alns.add_destroy_operator(destroyGreedyImageQuality)
    alns.add_destroy_operator(destroyCongestion)
    alns.add_repair_operator(repairRandom)
    alns.add_repair_operator(repairGreedy)
    alns.add_repair_operator(repairSmallTW)
    alns.add_repair_operator(repairCongestion)
   
    # Configure ALNS
    select = RandomSelect(num_destroy=3, num_repair=4)  # see alns.select for others
    accept = HillClimbing()  # see alns.accept for others
    stop = MaxIterations(maxItr)   # Create a new MaxRuntime instance for each run MaxRuntime(20)#NoImprovement(100) NoImprovement(10) #

    # Run the ALNS algorithm
    result = alns.iterate(state, select, accept, stop)

    # Retrieve the final solution
    # best = result.best_state
    # print(f"Best heuristic solution objective is {best.maxObjective[0]} and {best.maxObjective[1]}.")
    # result.plot_objectives()
    # plt.show()
    # print()
    return result, state



