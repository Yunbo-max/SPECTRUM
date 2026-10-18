def combinations_list(lst):
    # Initialize an empty list to store all combinations
    all_combinations = []
    # Loop through each element in the list
    for i in range(len(lst) + 1):
        # Generate all combinations of the current element with the rest of the list
        for combination in combinations(lst, i):
            # Append the combination to the all_combinations list
            all_combinations.append(combination)
    return all_combinations