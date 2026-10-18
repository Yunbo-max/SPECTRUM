def index_multiplication(tuple1, tuple2):
    # Initialize an empty list to store the result
    result = []
    # Iterate over the indices of the tuples
    for i in range(len(tuple1)):
        # Multiply the corresponding elements of the tuples and append to the result list
        result.append((tuple1[i][0] * tuple2[i][0], tuple1[i][1] * tuple2[i][1]))
    # Return the result list
    return result