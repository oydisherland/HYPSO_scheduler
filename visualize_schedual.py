from ALNS_algorithm import runALNS, createInitialSolution
from get_target_passes import getModelInput
from scheduling_model import SP, OH
import matplotlib.pyplot as plt


def printSchedual(schedual):

    # Extract data for plotting
    x_values = [ot.start for ot in schedual]
    y_values = range(len(schedual))  # Use the index as the y-value

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.scatter(x_values, y_values, c='blue', label='Observation Tasks')

    # Annotate each point with the target ID
    for i, ot in enumerate(schedual):
        annotation_text = f"{ot.GT.id} ({int(ot.start)})"
        plt.annotate(annotation_text, (x_values[i], y_values[i]), textcoords="offset points", xytext=(0, 10), ha='center')

    # Set labels and title
    plt.xlabel('Start Time')
    plt.ylabel('Observation Task Index')
    plt.title('Observation Tasks Start Times')
    plt.legend()
    plt.grid(True)
    plt.yticks([])
    plt.show()


# schedulingParameters = SP(20, 60, 90)
# oh, ttwList = getModelInput(50, 2, 2, 1)
# print(f"numbers of targets to choose from {len(ttwList)}")

# init_sol = createInitialSolution(ttwList, schedulingParameters, oh, destructionRate=0.3, maxSizeTabooBank=20)

# result, init_sol = runALNS(init_sol.otList, init_sol.ttwList, schedulingParameters, oh, destructionRate = 0.3, maxSizeTabooBank = 20)

# best = result.best_state
# print(f"Best heuristic solution objective is {best.maxObjective[0]} and {best.maxObjective[1]}.")

# schedual = best.otList
# printSchedual(init_sol.otList)
# printSchedual(schedual)