def find_combinations(tuples_list):
    # Initialize an empty list to store the combinations
    combinations = []
    # Iterate over each tuple in the list
    for tuple1 in tuples_list:
        # Iterate over each tuple in the list again
        for tuple2 in tuples_list:
            # Check if the tuples are not the same
            if tuple1 != tuple2:
                # Calculate the sum of the tuples
                sum1 = tuple1[0] + tuple1[1]
                sum2 = tuple2[0] + tuple2[1]
                # Check if the sums are not the same
                if sum1 != sum2:
                    # Append the combination to the list
                    combinations.append((sum1, sum2))
    # Return the list of combinations
    return combinations