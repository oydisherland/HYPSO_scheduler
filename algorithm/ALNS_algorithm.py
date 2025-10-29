from alns import ALNS
from alns.accept import SimulatedAnnealing
from alns.select import AlphaUCB
from alns.stop import MaxIterations

import numpy.random as rnd

from data_preprocessing.objective_functions import objectiveFunctionPriority, objectiveFunctionImageQuality
from scheduling_model import OH, SP, GSTW, OT, BT, DT, TTW
from algorithm.operators import repairOperator, destroyOperator, RepairType, DestroyType
from transmission_scheduling.input_parameters import TransmissionParams


class ProblemState:
    def __init__(self, otList, btList, dtList, ttwList, gstwList, oh, destructionNumber, schedulingParameters, transmissionParameters,
                 maxSizeTabooBank, isTabooBankFIFO):
        self.otList: list[OT] = otList
        self.btList: list[BT] = btList
        self.dtList: list[DT] = dtList
        self.ttwList: list[TTW] = ttwList
        self.gstwList: list[GSTW] = gstwList
        self.oh = oh
        self.destructionNumber = destructionNumber
        self.schedulingParameters = schedulingParameters
        self.transmissionParameters = transmissionParameters
        self.tabooBank = []
        self.maxSizeTabooBank = maxSizeTabooBank
        self.isTabooBankFIFO = isTabooBankFIFO
        self.objectiveValues = [0, 0] # Summed priority score and average image quality
        self.maxCapturePriority = max([ttw.GT.priority for ttw in ttwList])

    def objective(self) -> float:
        """
        Return the scaled objective values for the ALNS algorithm to minimize.
        """
        objective = sum(self.getScaledObjectiveValues())
        return -objective

    def getScaledObjectiveValues(self) -> tuple[float, float]:
        # Assume the max priority score is if the max amount of captures is scheduled with the highest priority found
        maxPrioritySchedule = self.schedulingParameters.maxCaptures * self.maxCapturePriority
        # Max image quality score is an average of 90 degrees elevation
        imageQualityMax = 90
        priority = self.objectiveValues[0] / maxPrioritySchedule
        # TODO make the scaling of image quality clearer and easier to adjust
        imageQuality = self.objectiveValues[1] / imageQualityMax * 0.25

        return priority, imageQuality

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
    ttwListResorted, otListAdjusted, btList, dtList, objectiveValues = repairOperator(
        ttwList, 
        otList,
        gstwList,
        tabooBank, 
        RepairType.RANDOM,
        schedulingParameters,
        transmissionParams,
        oh,
        True)
    
    state = ProblemState(otListAdjusted, btList, dtList, ttwListResorted, gstwList, oh, destructionNumber, schedulingParameters,
                         transmissionParams, maxSizeTabooBank, isTabooBankFIFO)
    state.objectiveValues = objectiveValues
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

def adjustTabooBank(current: ProblemState) -> list:
    # Remove targets from FIFO queue If the queue is full
    newTabooBank = current.tabooBank.copy()
    while len(newTabooBank) + current.destructionNumber >= current.maxSizeTabooBank:
        if len(newTabooBank) == 0:
            break
        # Remove the oldest target from the queue
        newTabooBank.pop(0)
    return newTabooBank


def getDestructionNumber(current: ProblemState) -> int:
    if len(current.tabooBank) + current.destructionNumber >= current.maxSizeTabooBank:
        # No targets can be removed
        return 0
    elif len(current.tabooBank) >= current.maxSizeTabooBank - current.destructionNumber:
        # Cannot remove as many targets as destruction dumber says
        return 1
    else: 
        return current.destructionNumber

### Destroy and repair operators ###

def destroyRandom(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    if current.isTabooBankFIFO:
        # Make space in the taboobank for new round of destructions
        newTabooBank = adjustTabooBank(current)
        numberOfTargetsToRemove = current.destructionNumber
    else:
        # Adjust destruction number after the size of the taboo bank
        newTabooBank = current.tabooBank.copy()
        numberOfTargetsToRemove = getDestructionNumber(current)

    otList, removedTargetsIdList = destroyOperator(
        current.otList,
        current.ttwList,
        numberOfTargetsToRemove, 
        DestroyType.RANDOM,
        current.oh,
        current.schedulingParameters.hypsoNr)

    destroyed = ProblemState(otList, current.btList, current.dtList, current.ttwList, current.gstwList, current.oh,
                 current.destructionNumber, current.schedulingParameters,
                 current.transmissionParameters, current.maxSizeTabooBank, current.isTabooBankFIFO)

    destroyed.objectiveValues = current.objectiveValues.copy()
    destroyed.tabooBank = newTabooBank
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed


def destroyGreedyPriority(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    if current.isTabooBankFIFO:
        # Make space in the taboobank for new round of destructions
        newTabooBank = adjustTabooBank(current)
        numberOfTargetsToRemove = current.destructionNumber
    else:
        # Adjust destruction number after the size of the taboo bank
        newTabooBank = current.tabooBank.copy()
        numberOfTargetsToRemove = getDestructionNumber(current)

    otList, removedTargetsIdList = destroyOperator(
        current.otList,
        current.ttwList,
        numberOfTargetsToRemove,
        DestroyType.GREEDY_P,
        current.oh,
        current.schedulingParameters.hypsoNr)

    destroyed = ProblemState(otList, current.btList, current.dtList, current.ttwList, current.gstwList, current.oh,
                             current.destructionNumber, current.schedulingParameters,
                             current.transmissionParameters, current.maxSizeTabooBank, current.isTabooBankFIFO)

    destroyed.objectiveValues = current.objectiveValues.copy()
    destroyed.tabooBank = newTabooBank
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed


def destroyGreedyImageQuality(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    if current.isTabooBankFIFO:
        # Make space in the taboobank for new round of destructions
        newTabooBank = adjustTabooBank(current)
        numberOfTargetsToRemove = current.destructionNumber
    else:
        # Adjust destruction number after the size of the taboo bank
        newTabooBank = current.tabooBank.copy()
        numberOfTargetsToRemove = getDestructionNumber(current)

    otList, removedTargetsIdList = destroyOperator(
        current.otList,
        current.ttwList,
        numberOfTargetsToRemove,
        DestroyType.GREEDY_IQ,
        current.oh,
        current.schedulingParameters.hypsoNr)

    destroyed = ProblemState(otList, current.btList, current.dtList, current.ttwList, current.gstwList, current.oh,
                             current.destructionNumber, current.schedulingParameters,
                             current.transmissionParameters, current.maxSizeTabooBank, current.isTabooBankFIFO)

    destroyed.objectiveValues = current.objectiveValues.copy()
    destroyed.tabooBank = newTabooBank
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed


def destroyCongestion(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    if current.isTabooBankFIFO:
        # Make space in the taboobank for new round of destructions
        newTabooBank = adjustTabooBank(current)
        numberOfTargetsToRemove = current.destructionNumber
    else:
        # Adjust destruction number after the size of the taboo bank
        newTabooBank = current.tabooBank.copy()
        numberOfTargetsToRemove = getDestructionNumber(current)

    otList, removedTargetsIdList = destroyOperator(
        current.otList,
        current.ttwList,
        numberOfTargetsToRemove,
        DestroyType.CONGESTION,
        current.oh,
        current.schedulingParameters.hypsoNr)

    destroyed = ProblemState(otList, current.btList, current.dtList, current.ttwList, current.gstwList, current.oh,
                             current.destructionNumber, current.schedulingParameters,
                             current.transmissionParameters, current.maxSizeTabooBank, current.isTabooBankFIFO)

    destroyed.objectiveValues = current.objectiveValues.copy()
    destroyed.tabooBank = newTabooBank
    destroyed.tabooBank.extend(removedTargetsIdList)
    return destroyed


def repairRandom(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    ttwList, otList, btList, dtList, objectiveValues = repairOperator(
        current.ttwList,
        current.otList,
        current.gstwList,
        current.tabooBank,
        RepairType.RANDOM, 
        current.schedulingParameters,
        current.transmissionParameters,
        current.oh)

    repaired = ProblemState(otList, btList, dtList, ttwList, current.gstwList, current.oh,
                 current.destructionNumber, current.schedulingParameters,
                 current.transmissionParameters, current.maxSizeTabooBank, current.isTabooBankFIFO)

    repaired.tabooBank = current.tabooBank.copy()
    repaired.objectiveValues = objectiveValues
    return repaired


def repairGreedy(current: ProblemState, rng: rnd.Generator) -> ProblemState: 
    ttwList, otList, btList, dtList, objectiveValues = repairOperator(
        current.ttwList,
        current.otList,
        current.gstwList,
        current.tabooBank,
        RepairType.GREEDY,
        current.schedulingParameters,
        current.transmissionParameters,
        current.oh)

    repaired = ProblemState(otList, btList, dtList, ttwList, current.gstwList, current.oh,
                 current.destructionNumber, current.schedulingParameters,
                 current.transmissionParameters, current.maxSizeTabooBank, current.isTabooBankFIFO)

    repaired.tabooBank = current.tabooBank.copy()
    repaired.objectiveValues = objectiveValues
    return repaired


def repairSmallTW(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    ttwList, otList, btList, dtList, objectiveValues = repairOperator(
        current.ttwList,
        current.otList,
        current.gstwList,
        current.tabooBank,
        RepairType.SMALL_TW,
        current.schedulingParameters,
        current.transmissionParameters,
        current.oh)

    repaired = ProblemState(otList, btList, dtList, ttwList, current.gstwList, current.oh,
                 current.destructionNumber, current.schedulingParameters,
                 current.transmissionParameters, current.maxSizeTabooBank, current.isTabooBankFIFO)

    repaired.tabooBank = current.tabooBank.copy()
    repaired.objectiveValues = objectiveValues
    return repaired


def repairCongestion(current: ProblemState, rng: rnd.Generator) -> ProblemState:
    ttwList, otList, btList, dtList, objectiveValues = repairOperator(
        current.ttwList,
        current.otList,
        current.gstwList,
        current.tabooBank,
        RepairType.CONGESTION,
        current.schedulingParameters,
        current.transmissionParameters,
        current.oh)

    repaired = ProblemState(otList, btList, dtList, ttwList, current.gstwList, current.oh,
                            current.destructionNumber, current.schedulingParameters,
                            current.transmissionParameters, current.maxSizeTabooBank, current.isTabooBankFIFO)

    repaired.tabooBank = current.tabooBank.copy()
    repaired.objectiveValues = objectiveValues
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
    state = ProblemState(initial_otList, [], [], initial_ttwList, gstwList, oh, destructionNumber, schedulingParameters,
                         transmissionParameters, maxSizeTabooBank, isTabooBankFIFO)
    state.objectiveValues = [objectiveFunctionPriority(initial_otList),
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
    # select = RouletteWheel(scores=[5, 2, 1, 0.5], decay=0.8, num_destroy=3, num_repair=4)
    select = AlphaUCB(scores = [5, 2, 1, 0.5], alpha=0.1, num_destroy=3, num_repair=4)
    # Start configuration
    #accept = SimulatedAnnealing(start_temperature=100, end_temperature=1, step=0.99) 
    # Moderate
    #accept = SimulatedAnnealing(start_temperature=500, end_temperature=1, step=0.99)
    # Aggressive (fast cooling)
    accept = SimulatedAnnealing(start_temperature=0.06, end_temperature=0.0001, step=0.95)
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
    return result



