using JuMP 
using GLPK
using DataFrames
using CSV

# Include the file containing the extract_Targetdata function
include("extract_targetData.jl")

# Extract the target data
names, longitude, latitude, minElevations, maxClouds, priority, reference_StartTime, allStartTimes = extract_Targetdata()

#Some parameters
capture_time = 2 * 60 #2 min
timewindow_days = 2
nrOfTargets = 1:length(allStartTimes)
big_M = 180000
nrOfTimeSteps = 1:length(allStartTimes[1])
cap_per_time = 4
maxCap = 40

println("Time discretization = 20 sec, give ", length(allStartTimes[1]), " number of timesteps" )

#defining the optimizing Model
model = Model(GLPK.Optimizer)

# DECISION VARIABLES
@variable(model, x[i in nrOfTargets, ts in nrOfTimeSteps], Bin)

# OBJECTION FUNCTION
@objective(model, Max, sum(priority[i] * sum(x[i, ts] for ts in nrOfTimeSteps) for i in nrOfTargets))

# CONSTRAINTS
@constraint(model, [i in nrOfTargets], sum(x[i, ts] for ts in nrOfTimeSteps) <= 1) #only one cap / target

@constraint(model, [ts in 1:(length(allStartTimes[1])-cap_per_time)], sum(sum(x[:,ts + i]) for i in 0:cap_per_time) <= 1) #timesteps between each capture

@constraint(model, sum(x[i, ts] for i in nrOfTargets, ts in nrOfTimeSteps) <= maxCap) #maximum cap / time window

@constraint(model, [i in nrOfTargets, j in nrOfTimeSteps], x[i, j] <= allStartTimes[i][j]) #only cap if target is available

# OPTIMIZE MODEL
println("Start optimizing")
elapsed_time = @elapsed optimize!(model)
println("Optimization took ", elapsed_time, " seconds")

#print the results and extracting the targets
capturedTargets = Dict()
for i in nrOfTargets
    for ts in nrOfTimeSteps
        if value(x[i, ts]) == 1
            println("Target ", names[i], " is captured at time ", ts)
            capturedTargets[i] = ts
        end
    end
end

#calculate nr of possible captures
global totalPossibleCaptures = 0
for i in eachindex(allStartTimes)
    for ts in eachindex(allStartTimes[1])
        if allStartTimes[i][ts] == 1
            global totalPossibleCaptures += 1
        end
    end
end


# Write the DataFrame to a CSV file (append mode)
results_df = DataFrame( 
    NrOf_targets = length(allStartTimes),
    NrOf_captures = totalPossibleCaptures,   
    Time_elapsed = elapsed_time,
    Discretization = 50,
    Cap_per_time = cap_per_time,
    max_captures = maxCap)


open("results.csv", "a") do file
    CSV.write(file, results_df; append=true)
end

# Write the capture times to a CSV file (append mode)


for (index, ts) in capturedTargets
    capture_df = DataFrame(
        Target = names[index],
        Capture_time = ts,
        Time_elapsed = elapsed_time,
        Discretization = 50,
        Cap_per_time = cap_per_time,
        Weight = priority[index],
        ReferenceTime = reference_StartTime)
    open("capture_times.csv", "a") do file
        CSV.write(file, capture_df; append=true)
    end
end
