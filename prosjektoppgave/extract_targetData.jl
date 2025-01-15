using JuMP
using DataFrames
using CSV
using Dates
using Random


#
#   Function to split a string by commas unless the comma is inside parentheses
#
function split_by_commas_outside_parentheses(s::String)
    result = []
    buffer = ""
    depth = 0
    for c in s
        if c == ',' && depth == 0
            push!(result, buffer)
            buffer = ""
        else
            if c == '('
                depth += 1
            elseif c == ')'
                depth -= 1
            end
            buffer *= c
        end
    end
    push!(result, buffer)
    return result
end

#
#   Calculates the difference in seconds between the two DateTime objects
#
function seconds_difference(time1::DateTime, time2::DateTime)::Float64
    difference = time2 - time1
    return Dates.value(difference) / 1e3  # Convert milliseconds to seconds
end


#
#   Extract the datetime part from python-type datetime string
#
function parse_datetime(dt_str::String)::DateTime
    # Match the datetime string with or without seconds
    m = match(r"datetime\.datetime\((\d+),(\d+),(\d+),(\d+),(\d+)(?:,(\d+))?", dt_str)
    if m === nothing
        error("Failed to parse datetime string: $dt_str")
    end
    dt_part = m.captures
    year, month, day, hour, minute = parse.(Int, dt_part[1:5])
    second = dt_part[6] !== nothing ? parse(Int, dt_part[6]) : 0
    return DateTime(year, month, day, hour, minute, second)
end


function simulate_cloud_obscuring(allStartTimes)
    
    # Find the total number of possible captures
    global totalPossibleCaptures = 0
    possibleStartTime_dict = Dict()
    for i in eachindex(allStartTimes)
        for ts in eachindex(allStartTimes[1])
            if allStartTimes[i][ts] == 1
                global totalPossibleCaptures += 1
                possibleStartTime_dict[totalPossibleCaptures] = (i, ts)
            end
        end
    end

    # Remove 40% of the captures due to cloud obscuration
    cloudObscuringPersentage = 0.4
    nrOf_CloudObscuredCaptures = Int(ceil(cloudObscuringPersentage * totalPossibleCaptures))
    println("Removing ", cloudObscuringPersentage, "% of captures due to cloud obscuration")
    
    # Remove nrOf_CloudObscuredCaptures start times from allStartTimes list randomly
    previouslyRemovedTargets = []
    for i in 1:nrOf_CloudObscuredCaptures
        random_int = rand(1:totalPossibleCaptures)
        while random_int in previouslyRemovedTargets
            random_int = rand(1:totalPossibleCaptures)
        end
        i, ts = possibleStartTime_dict[random_int]
        allStartTimes[i][ts] = 0
        push!(previouslyRemovedTargets, random_int)
    end

    return allStartTimes
end


function removeEmptyRows(allStartTimes, names)

    reducedStartTimes = []
    reducedNames = []
    for i in eachindex(allStartTimes)
        global targetCanBeCaptured = false
        for st in eachindex(allStartTimes[1])
            if allStartTimes[i][st] == 1
                global targetCanBeCaptured = true
                break
            end
        end
        if targetCanBeCaptured == true
            push!(reducedStartTimes, allStartTimes[i])
            push!(reducedNames, names[i])
        end
    end
    println("Reducing targetList from ", length(allStartTimes) ," to ",length(reducedStartTimes))
    return reducedStartTimes, reducedNames
end
#
#   Function to extract the target data from the CSV file
#
function extract_Targetdata()

    DATA_DIR = "updated_targets.csv"

    # Read the preprocessed CSV file into a DataFrame
    targets_df = CSV.read(DATA_DIR, DataFrame, header = true)

    # Defining some variables
    num_rows = size(targets_df, 1)
    delta_t = 50 # Time discretization
    timeWindow = 2 # Time window in days

    # Extract the target data into separate arrays
    names = Containers.DenseAxisArray(targets_df[!, 1], 1:num_rows)
    longitude = Containers.DenseAxisArray(targets_df[!, 2], 1:num_rows)
    latitude = Containers.DenseAxisArray(targets_df[!, 3], 1:num_rows)
    minElevations = Containers.DenseAxisArray(targets_df[!, 4], 1:num_rows)
    maxClouds = Containers.DenseAxisArray(targets_df[!, 5], 1:num_rows)
    priority = Containers.DenseAxisArray(targets_df[!, 6], 1:num_rows)

    startTimes_rawData = Array(targets_df[!, 10])
    endTimes_rawData = Array(targets_df[!, 11])

    ### Extract the start- and end-times for each target ####
    # Iterate through each start- and end-time, 
    # startTime_rawData and endTime_rawData shall have the same length
    # remove the brackets, whitespaces, and single quotes, and save in new array
    startTimes = []
    endTimes = []
    for i in eachindex(startTimes_rawData)
        
        # Split the string by commas unless the comma is inside parentheses
        SingleTarget_startTime = split_by_commas_outside_parentheses(startTimes_rawData[i])
        SingleTarget_endTime = split_by_commas_outside_parentheses(endTimes_rawData[i])
        
        # Remove the brackets
        SingleTarget_startTime[1] = strip(SingleTarget_startTime[1], ['['])
        SingleTarget_startTime[end] = strip(SingleTarget_startTime[end], [']'])
        SingleTarget_endTime[1] = strip(SingleTarget_endTime[1], ['['])
        SingleTarget_endTime[end] = strip(SingleTarget_endTime[end], [']'])

        # Remove the whitespaces
        SingleTarget_startTime = [replace(x, " " => "") for x in SingleTarget_startTime]
        SingleTarget_endTime = [replace(x, " " => "") for x in SingleTarget_endTime]

        # Remove the single quotes
        filter!(x -> x != "''", SingleTarget_startTime)
        filter!(x -> x != "''", SingleTarget_endTime)

        # Add the start-/ end-time for a single target as one element in the arrays
        push!(startTimes, SingleTarget_startTime)
        push!(endTimes, SingleTarget_endTime)
    end

    # Create an array of relative start times for each target. Each time is relative to earliest possible capture
    relative_StartTimes = []
    # Reference time for the relative start times, make this become the earliest possible capture time
    reference_StartTime = DateTime(2025, 1, 15, 10, 0, 0)  
    for i in eachindex(startTimes)  

        relativeStartTimes_i = []
        
        for j in 1:(length(startTimes[i]))

            time1 = parse_datetime(startTimes[i][j])
            time2 = parse_datetime(endTimes[i][j])
            time1_relative = seconds_difference(reference_StartTime, time1)
            time2_relative = seconds_difference(reference_StartTime, time2)

            # negative diff value means that there is not enough time to capture
            difference = time2_relative - time1_relative
            difference < 0 ? continue : nothing

            # rst (relative start time) represents the time difference in seconds
            # between now and capture j 
            rst = time1_relative
            push!(relativeStartTimes_i, rst)

            # Add all additional capture start times that are possible with the given discretization
            while rst + delta_t < time2_relative 
                rst += delta_t
                push!(relativeStartTimes_i, rst)
            end
        end

        push!(relative_StartTimes, relativeStartTimes_i)
    end


    nrOfTimeSteps = Int(timeWindow * 24 * 60 * 60 / delta_t) # Number of 20 sec time-steps in the 2 day time-window
    allStartTimes = []

    # add all possible start times for one target at a time
    for i in eachindex(startTimes) 
        
        startTimes_oneTarget = [0 for k in 1:nrOfTimeSteps]

        #check at each timestep if the target can be captured
        for timeStep in 1:nrOfTimeSteps

            time = timeStep * delta_t
            # check all the startTimes that are possible for the target i
            for j in 1:(length(startTimes[i]))

                time1 = parse_datetime(startTimes[i][j])
                time2 = parse_datetime(endTimes[i][j])
                time_earliestCapture = seconds_difference(reference_StartTime, time1)
                time_latestCapture = seconds_difference(reference_StartTime, time2)
                
                #check if the timestep is within the capture window
                if time >= time_earliestCapture && time <= time_latestCapture
                    startTimes_oneTarget[timeStep] = 1
                end
            end
        end
        # add the start times for target i
        push!(allStartTimes, startTimes_oneTarget)
    end

    println("Target data extracted successfully!")

    # Simulate cloud obscuring
    #allStartTimes_wCloudObscuring = simulate_cloud_obscuring(allStartTimes)
    allStartTimes_wCloudObscuring = allStartTimes
    # Remove empty rows
    reducedStartTimes, reducedNames = removeEmptyRows(allStartTimes_wCloudObscuring, names)

    return reducedNames, longitude, latitude, minElevations, maxClouds, priority, reference_StartTime, reducedStartTimes

end








