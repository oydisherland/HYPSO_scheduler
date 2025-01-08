# Write the DataFrame to a CSV file
# results_df = DataFrame( 
#     NrOf_targets = length(allStartTimes),
#     NrOf_captures = totalPossibleCaptures,   
#     Time_elapsed = elapsed_time,
#     Discretization = 30,
#     Cap_per_time = cap_per_time)

# # Write the DataFrame to a CSV file (append mode)
# open("results.csv", "a") do file
#     CSV.write(file, results_df; append=true)
# end