def sum_list(list1, list2):
    # Initialize an empty list to store the sum of corresponding elements
    result = []
    # Iterate over the indices of the lists
    for i in range(len(list1)):
        # Add the corresponding elements from both lists and append to the result list
        result.append(list1[i] + list2[i])
    # Return the resulting list
    return result