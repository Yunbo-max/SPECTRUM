def consecutive_duplicates(lst):
    # Initialize an empty list to store the result
    result = []
    # Iterate through the list
    for i in range(len(lst)):
        # If the current element is not the same as the previous one, add it to the result list
        if i == 0 or lst[i] != lst[i-1]:
            result.append(lst[i])
    return result