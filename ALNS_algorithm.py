from alns import ALNS
from alns.accept import HillClimbing, SimulatedAnnealing
from alns.select import RandomSelect
from alns.stop import MaxRuntime, NoImprovement

import numpy.random as rnd
import copy
import matplotlib.pyplot as plt
import math

from scheduling_model import OH, GT, TW, TTW, OT ,SP
from get_target_passes import getModelInput
from operators import repairOperator, destroyOperator, RepairType, DestroyType, testThisShit




class ProblemState:
    # TODO add attributes that encode a solution to the problem instance

    ###
    def __init__(self, otList, ttwList, oh, destructionRate, schedulingParameters, maxSizeTabooBank):
        self.otList = otList
        self.ttwList = ttwList
        self.oh = oh
        self.destructionRate = destructionRate
        self.schedulingParameters = schedulingParameters
        self.tabooBank = []
        self.maxSizeTabooBank = maxSizeTabooBank
        self.maxObjective = 0
    ###

    def objective(self) -> float:
        # TODO implement the objective function
        ###
        sum = 0
        for ot in self.otList:
            sum += ot.GT.priority
            #Negating the sum since the alns solves the minimization problem
        return -sum
        ###

    def get_context(self):
        # TODO implement a method returning a context vector. This is only
        #  needed for some context-aware bandit selectors from MABWiser;
        #  if you do not use those, this default is already sufficient!
        return None


def initial_state(schedulingParameters: SP, ttwList: list, oh: OH, destructionRate: float, maxSizeTabooBank: int) -> ProblemState:
    # TODO implement a function that returns an initial solution
    ### ttwsGreedy, _ , objectiveValuesList
    otList = []
    tabooBank = []
    ttwListResorted, otList, objectiveVal = repairOperator(ttwList, otList, tabooBank, RepairType.RANDOM, schedulingParameters, oh)
    state = ProblemState(otList, ttwListResorted, oh, destructionRate, schedulingParameters, maxSizeTabooBank)
    state.maxObjective = objectiveVal[0]
    return state
    ###


def destroyRandom(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # TODO implement how to destroy the current state, and return the destroyed
    #  state. Make sure to (deep)copy the current state before modifying!
    ###
    destructionNumber = 1 if current.maxSizeTabooBank > len(current.tabooBank) else 0
    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(destroyed.otList, destructionNumber, DestroyType.RANDOM)
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed
    ###

def destroyGreedy(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # TODO implement how to destroy the current state, and return the destroyed
    #  state. Make sure to (deep)copy the current state before modifying!
    ###
    destructionNumber = 1 if current.maxSizeTabooBank > len(current.tabooBank) else 0
    destroyed = copy.deepcopy(current)
    destroyed.otList, removedTargetsIdList = destroyOperator(destroyed.otList, destructionNumber, DestroyType.GREEDY)
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed
    ###

def repairRandom(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # TODO implement how to repair a destroyed state, and return it
    ### 
    repaired = copy.deepcopy(current)
    
    repaired.ttwList, repaired.otList, objectiveVal = repairOperator(repaired.ttwList, repaired.otList, repaired.tabooBank, RepairType.RANDOM, repaired.schedulingParameters, repaired.oh)
    if objectiveVal[0] > repaired.maxObjective:
        repaired.maxObjective = objectiveVal[0]
    return repaired
    ###

def repairGreedy(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    # TODO implement how to repair a destroyed state, and return it
    ### 
    repaired = copy.deepcopy(current)

    repaired.ttwList, repaired.otList, objectiveVal = repairOperator(repaired.ttwList, repaired.otList, repaired.tabooBank, RepairType.GREEDY, repaired.schedulingParameters, repaired.oh)
    if objectiveVal[0] > repaired.maxObjective:
        repaired.maxObjective = objectiveVal[0]
    return repaired
    ###

# Function to run ALNS algorithm
def run_alns(schedulingParameters: SP, ttwList: list, oh: OH, destructionRate: float, maxSizeTabooBank: int):
    # Create the initial solution
    init_sol = initial_state(schedulingParameters, ttwList, oh, destructionRate, maxSizeTabooBank)
    print(f"Initial solution objective is {init_sol.maxObjective}.")

    # Run the greedy algorithm 
    otListEmpty = []
    newTabooBank = []
    _, _, objectiveValGreedy = repairOperator(init_sol.ttwList.copy() , otListEmpty, newTabooBank, RepairType.GREEDY, SP(20, 60, 90), init_sol.oh)
    print(f"Greedy solution objective is {objectiveValGreedy[0]}.")

    # Create ALNS and add one or more destroy and repair operators
    alns = ALNS.ALNS()  # Initialize without a random seed
    alns.add_destroy_operator(destroyRandom)
    alns.add_destroy_operator(destroyGreedy)
    alns.add_repair_operator(repairRandom)
    alns.add_repair_operator(repairGreedy)
   
    # Configure ALNS
    select = RandomSelect(num_destroy=2, num_repair=2)  # see alns.select for others
    accept = HillClimbing()  # see alns.accept for others
    stop = NoImprovement(1000)  # Create a new MaxRuntime instance for each run

    # Run the ALNS algorithm
    result = alns.iterate(init_sol, select, accept, stop)

    # Retrieve the final solution
    best = result.best_state
    print(f"Best heuristic solution objective is {best.maxObjective}.")
    # result.plot_objectives()
    # plt.show()
    print()

oh, ttwList = getModelInput(50, 2, 2, 1)
for ttw in ttwList:
    print(f"Target {ttw.GT.id} has {len(ttw.TWs)} time windows")
# Run ALNS multiple times
for i in range(3):
    print(f"Run {i+1}:")

    schedulingParameters = SP(20, 60, 90)
    oh, ttwList = getModelInput(50, 2, 2, 1)
    print(f"numbers of targets to schoose from {len(ttwList)}")

    run_alns(schedulingParameters, ttwList, oh, destructionRate = 0.1, maxSizeTabooBank = 5)
    print("--------------------------------------------------------------")


