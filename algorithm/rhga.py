from scheduling_model import OH, OT, SP, generateTaskID
import random


def RHGA(ttwList: list, otList: list, unfeasibleTargetsIdList: list, schedulingParameters: SP, oh: OH, greedyMode: bool, randomtwDistrobution = True):
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
    for ttw in ttwList:
        if len(otList) == schedulingParameters.maxCaptures:
            # Maximum number of captures are scheduled, end loop
            break
        if ttw.GT.id in unfeasibleTargetsIdList:
            # Target is maked unfeasible, skip to next target
            continue

        bufferTime = schedulingParameters.captureDuration + schedulingParameters.transitionTime

        # Loop through a target's time windows
        for tw in ttw.TWs:   
            newObservationStart = tw.start
            

            if greedyMode:
                # select start time when image quality is highest
                newObservationStart = tw.start + (tw.end - tw.start) / 2 - schedulingParameters.captureDuration / 2
                
            elif randomtwDistrobution:
                # Randomly select a time within the time window
                newObservationStart = random.uniform(tw.start, tw.end - schedulingParameters.captureDuration)

            solutionIsFeasible = True

            # Find an observation time within tw that does not collide with already scheduled observation tasks
            for ot in otList:

                if ot.start > newObservationStart + bufferTime or ot.end + schedulingParameters.transitionTime < newObservationStart:
                    # No collision with current ot, continue to check next ot
                    continue
                elif ot.start + bufferTime*2 < tw.end:
                    # The target can be observed after the current ot, continue to check the next ot with updated newObservationStart
                    newObservationStart = ot.start + bufferTime
                    continue
                else:
                    # Collision is inevitable, check the next time window
                    solutionIsFeasible = False
                    break

            if solutionIsFeasible:
                # Solution is feasible, add the observation task to the schedule
                newOT = OT(
                    generateTaskID(ttw.GT.id, newObservationStart),
                    ttw.GT,
                    newObservationStart,
                    newObservationStart + schedulingParameters.captureDuration
                )
                otList.append(newOT)
                break
        

    # Check for duplicates
    # ot_counts = Counter(otList)
    # duplicates = [ot for ot, count in ot_counts.items() if count > 1]
    # if duplicates:
    #     print("Duplicate observation tasks found after rnsga loop:", duplicates)

    return otList




