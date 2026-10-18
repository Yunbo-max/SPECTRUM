def merge(list_of_lists):
    # Initialize two empty lists to store the merged results
    result = []
    # Iterate over each sublist in the input list
    for sublist in list_of_lists:
        # Append the first element of the sublist to the first list in the result
        result[0].append(sublist[0])
        # Append the second element of the sublist to the second list in the result
        result[1].append(sublist[1])
    # Return the merged list of lists
    return result