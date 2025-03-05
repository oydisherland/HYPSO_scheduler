from objective_functions import objectiveFunctionPriority, objectiveFunctionImageQuality
from scheduling_model import OH, GT, TW, TTW, OT ,SP
import random


def RHGA(ttwList: list, otList: list, unfeasibleTargetsIdList: list, schedulingParameters: SP, oh: OH, randomtwDistrobution = True):
    """
    Random Heuristic Greedy Algorithm:
    1. Encode GT and TW data
    2. Select a target in the order of the list (algorithm is prioritizing targets earlier in the list)
    3. See if target can be included in a feasible schedule
    4. Calculate the objective value(s)

    Output:
    - otList: scheduled observation tasks
    - objectiveValues: objective values [priority, image quality]
    """

    # Loop through the targets
    for _, ttw in enumerate(ttwList):
        if len(otList) == schedulingParameters.maxCaptures:
            # Maximum number of captures are scheduled, end loop
            break
        if ttw.GT.id in unfeasibleTargetsIdList:
            # Target is maked unfeasible, skip to next target
            continue

        bufferTime = schedulingParameters.captureDuration + schedulingParameters.transitionTime

        # Loop through a target's time windows
        for tw in ttw.TWs:   
            newObeservationStart = tw.start
            
            if randomtwDistrobution:
                # Randomly select a time within the time window
                newObeservationStart = random.uniform(tw.start, tw.end - bufferTime)

            solutionIsFeasible = True

            # Find an observation time within tw that does not collide with already scheduled observation tasks
            for ot in otList:
                if(ot.GT.id == ttw.GT.id):
                    # Target is already scheduled, solution is not feasible
                    solutionIsFeasible = False
                    break

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
        
    
    objectiveValues = []
    objectiveValues.append(objectiveFunctionPriority(otList))
    objectiveValues.append(objectiveFunctionImageQuality(otList, oh))

    return otList, objectiveValues




