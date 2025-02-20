from objective_functions import objectiveFunctionPriority
from scheduling_model import OH, GT, TW, TTW, OT ,SP
import random



""" Random Heuristic Greedy Algorithm """
def RHGA(ttwList: list, schedulingParameters: SP, randomtwDistrobution = True):
    """
    1. Encode GT and TW data
    2. Select a target in the order of the list (algorithm is prioritizing targets earlier in the list)
    3. See if target can be included in a feasible schedule
    4. Calculate the objective value(s)

    DecicionVariable
     - ot.start     : floating variable indication what time during the corresponding time window the observation starts, size = number of observation tasks
    """
    otList = []

    # Loop through the targets
    for index, ttw in enumerate(ttwList):    
        bufferTime = schedulingParameters.captureDuration + schedulingParameters.transitionTime

        # Loop through a target's time window in chronological order
        for tw in ttw.TWs:   
            newObeservationStart = tw.start
            
            if randomtwDistrobution:
                # Randomly select a time within the time window
                newObeservationStart = random.uniform(tw.start, tw.end - bufferTime)

            solutionIsFeasible = True

            # Find an observation time within tw that does not collide with already scheduled observation tasks
            for ot in otList:
                if ot.start > newObeservationStart + bufferTime or ot.start + bufferTime < newObeservationStart:
                    # No collision with current ot, continue to check next ot
                    continue
                elif ot.start + bufferTime > tw.end:
                    # The the target can be observed after the current ot
                    newObeservationStart = ot.start + bufferTime
                    # Continue to check the next ot with updated newObeservationStart
                    continue
                else:
                    # Collision is inevitable, check the next time window
                    solutionIsFeasible = False
                    break

            if solutionIsFeasible:
                # Solution is feasible, add the observation task to the schedule
                otList.append(OT(ttw.GT, newObeservationStart, newObeservationStart + bufferTime))
                break
        
        if len(otList) == schedulingParameters.maxCaptures:
            # Maximum number of captures are reached, end loop
            break
    
    objectiveValues = []
    objectiveValues.append(objectiveFunctionPriority(otList))

    return otList, objectiveValues



# schedulingParameters = SP(20, 60, 90)

# oh, ttws = getModelInput(50, 2, 2, 30)

# otList, objectiveValuesList = RHGA(ttws, schedulingParameters)
# for ov in objectiveValuesList:
#     print("Objective value original: ", ov)

# ttwsRandom = operators.randomSort(ttws)
# otList, objectiveValuesList = RHGA(ttwsRandom, schedulingParameters)
# for ov in objectiveValuesList:
#     print("Objective value random: ", ov)

# ttwsGreedy = operators.greedySort(ttwsRandom)
# otList, objectiveValuesList = RHGA(ttwsGreedy, schedulingParameters)
# for ov in objectiveValuesList:
#     print("Objective value greedy: ", ov)

# ttwsSmallTW = operators.smallTWSort(ttwsGreedy)
# otList, objectiveValuesList = RHGA(ttwsSmallTW, schedulingParameters)
# for ov in objectiveValuesList:
#     print("Objective value smallTW: ", ov)

# ttwsCongestion = operators.congestionSort(ttwsSmallTW)
# otList, objectiveValuesList = RHGA(ttwsCongestion, schedulingParameters)
# for ov in objectiveValuesList:
#     print("Objective value congestion: ", ov)

