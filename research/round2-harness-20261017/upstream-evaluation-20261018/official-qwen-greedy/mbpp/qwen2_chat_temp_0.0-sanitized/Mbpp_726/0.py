def multiply_elements(tup):
    # Initialize an empty list to store the result
    result = []
    # Iterate through the tuple using a for loop
    for i in range(len(tup) - 1):
        # Multiply the current element with the next element and append to the result list
        result.append(tup[i] * tup[i + 1])
    # Convert the list to a tuple and return it
    return tuple(result)