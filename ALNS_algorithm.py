from alns import ALNS
from alns.accept import HillClimbing, SimulatedAnnealing
from alns.select import RandomSelect
from alns.stop import MaxRuntime, NoImprovement

import numpy.random as rnd
import copy
import matplotlib.pyplot as plt

from scheduling_model import OH ,SP
from operators import repairOperator, destroyOperator, RepairType, DestroyType

class ProblemState:
    def __init__(self, otList, ttwList, oh, destructionRate, schedulingParameters, maxSizeTabooBank):
        self.otList = otList
        self.ttwList = ttwList
        self.oh = oh
        self.destructionRate = destructionRate
        self.schedulingParameters = schedulingParameters
        self.tabooBank = []
        self.maxSizeTabooBank = maxSizeTabooBank
        self.maxObjective = [0, 0]
        self.imageQuality = 0

    def objective(self) -> float:
        sum = 0
        for ot in self.otList:
            sum += ot.GT.priority
            #Negating the sum since the alns solves the minimization problem
        sum += self.imageQuality
        return -sum

    def get_context(self):
        # TODO implement a method returning a context vector. This is only
        #  needed for some context-aware bandit selectors from MABWiser;
        #  if you do not use those, this default is already sufficient!
        return None


def initial_state(otList: list, ttwList: list, schedulingParameters: SP, oh: OH, destructionRate: float, maxSizeTabooBank: int) -> ProblemState:
    tabooBank = []
    ttwListResorted, otList, objectiveValues = repairOperator(
        ttwList, 
        otList, 
        tabooBank, 
        RepairType.RANDOM, 
        schedulingParameters, 
        oh)
    
    state = ProblemState(otList, ttwListResorted, oh, destructionRate, schedulingParameters, maxSizeTabooBank)
    state.maxObjective = objectiveValues
    return state


def destroyRandom(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # Make sure to (deep)copy the current state before modifying!
    destructionNumber = 1 if current.maxSizeTabooBank > len(current.tabooBank) else 0
    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(
        destroyed.otList, 
        destroyed.ttwList,
        destructionNumber, 
        DestroyType.RANDOM,
        destroyed.oh)
    
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed


def destroyGreedyPriority(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # Make sure to (deep)copy the current state before modifying!
    destructionNumber = 1 if current.maxSizeTabooBank > len(current.tabooBank) else 0
    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(
        destroyed.otList, 
        destroyed.ttwList,
        destructionNumber, 
        DestroyType.GREEDY_P,
        destroyed.oh)
    
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed

def destroyGreedyImageQuality(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # Make sure to (deep)copy the current state before modifying!
    destructionNumber = 1 if current.maxSizeTabooBank > len(current.tabooBank) else 0
    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(
        destroyed.otList, 
        destroyed.ttwList,
        destructionNumber, 
        DestroyType.GREEDY_IQ,
        destroyed.oh)
    
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed

def destroyCongestion(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # Make sure to (deep)copy the current state before modifying!
    destructionNumber = 1 if current.maxSizeTabooBank > len(current.tabooBank) else 0
    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(
        current.otList, 
        current.ttwList,
        destructionNumber, 
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

def createInitialSolution(ttwList: list, schedulingParameters: SP, oh: OH, destructionRate: float, maxSizeTabooBank: int):
    
    # Create the initial solution
    otListEmpty = []
    init_sol = initial_state(otListEmpty, ttwList, schedulingParameters, oh, destructionRate, maxSizeTabooBank)
    
    return init_sol

# Function to run ALNS algorithm
def runALNS( inital_otList: list, initial_ttwList: list, schedulingParameters: SP, oh: OH, destructionRate: float, maxSizeTabooBank: int):
    
    # Format the problem state
    state = ProblemState(inital_otList, initial_ttwList, oh, destructionRate, schedulingParameters, maxSizeTabooBank)
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
    stop = MaxRuntime(10)   # Create a new MaxRuntime instance for each run MaxRuntime(20)#NoImprovement(100)

    # Run the ALNS algorithm
    result = alns.iterate(state, select, accept, stop)

    # Retrieve the final solution
    # best = result.best_state
    # print(f"Best heuristic solution objective is {best.maxObjective[0]} and {best.maxObjective[1]}.")
    # result.plot_objectives()
    # plt.show()
    # print()
    return result, state



