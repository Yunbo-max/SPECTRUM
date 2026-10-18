def find_tuples(tuples_list, k):
    # Initialize an empty list to store tuples that meet the condition
    result = []
    # Iterate through each tuple in the list
    for tup in tuples_list:
        # Check if all elements in the tuple are divisible by k
        if all(element % k == 0 for element in tup):
            # If the condition is met, append the tuple to the result list
            result.append(tup)
    # Return the list of tuples that meet the condition
    return result