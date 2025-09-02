import numpy as np
from scheduling_model import SP, OH
import matplotlib.pyplot as plt
from pymoo.visualization.scatter import Scatter


def createPlotSchedual(schedual, filename, showPlot):

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
    plt.savefig(filename, format='pdf', dpi=300) 
    if showPlot:
        plt.show()
    plt.close()

def createPlotObjectiveSpace(fronts, objectiveSpace, F_selected, filename, showPlot):

    pareto_front_indices = fronts[0]

    # Ensure pareto_front_indices is a valid index
    pareto_front_indices = np.array(pareto_front_indices, dtype=int).flatten()
    # Ensure objectiveSpace is a NumPy array
    objectiveSpace = np.array(objectiveSpace)

    pareto_front = objectiveSpace[pareto_front_indices]
    F_selected = np.array(F_selected)

    plot = Scatter(title="Pareto Front")
    plot.add(objectiveSpace, color="blue")
    plot.add(pareto_front, facecolor="green")
    plot.add(F_selected, facecolor="none", edgecolor="red")
    plot.save(filename, format='pdf', dpi=300) 
    if showPlot:
        print("Displaying plot...")
        plot.show()
    plt.close()
    

def createPlotKneePointHistogram(bestObjectivesHistory, filename, showPlot):
    # Create a histogram of the best solution objective values
    x_values = [obj[0] for obj in bestObjectivesHistory]
    y_values = [obj[1] for obj in bestObjectivesHistory]
    plt.figure(figsize=(10, 6))
    plt.scatter(x_values, y_values, c='blue', label='Observation Tasks')

    similarIndices = []
    for i in range(len(bestObjectivesHistory)):
        if i != len(bestObjectivesHistory)-1:
            if x_values[i] == x_values[i+1] and y_values[i] == y_values[i+1]:
                similarIndices.append(i)
                continue
        if similarIndices != []:
            text = f"{similarIndices[0]} to {i}"
        else:
            text = f"{i}"
        plt.annotate(text, (x_values[i], y_values[i]), textcoords="offset points", xytext=(0, 10), ha='center')
        similarIndices.clear()

    plt.xlabel('Priority')
    plt.ylabel('Image Quality')
    plt.savefig(filename, format='pdf', dpi=300) 
    if showPlot:
        plt.show()
    plt.close()
