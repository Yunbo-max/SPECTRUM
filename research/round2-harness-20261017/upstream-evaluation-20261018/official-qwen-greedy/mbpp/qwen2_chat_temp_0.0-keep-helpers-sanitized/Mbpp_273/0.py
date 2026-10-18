def substract_elements(tuple1, tuple2):
    # Initialize an empty list to store the result
    result = []
    # Iterate over the indices of the tuples
    for i in range(len(tuple1)):
        # Subtract the corresponding elements and append to the result list
        result.append(tuple1[i] - tuple2[i])
    # Return the result as a tuple
    return tuple(result)