using CSV
using DataFrames

arr = [1 0 0 0 0 0; 0 0 0 1 0 0; 0 0 0 0 0 1]
rows = 3
colms = 6

for c in 1:(colms - 2)
    result = sum(sum(arr[:, c + i]) for i in 0:2)
    if result > 1
        println(c, " - Targets too close, result = "  , result)
    end
end

names = ["A", "B", "C", "D", "E", "F"]
totalPossibleCaptures = 3
elapsed_time = 33
cap_per_time = 4
reference_StartTime = 0

capturedTargets = Dict()
capturedTargets[1] = 3
capturedTargets[2] = 5
capturedTargets[3] = 1

priority = [3, 4, 5, 4, 3, 2, 5, 6]

for (index, ts) in capturedTargets
    capture_df = DataFrame(
        Target = names[index],
        Capture_time = ts,
        Time_elapsed = elapsed_time,
        Discretization = 30,
        Cap_per_time = cap_per_time,
        Weight = priority[index],
        ReferenceTime = reference_StartTime)
    open("capture_times.csv", "a") do file
        CSV.write(file, capture_df; append=true)
    end
end

