def remove_nested(tup):
    # Initialize an empty list to store the non-tuple elements
    result = []
    # Iterate through each element in the tuple
    for element in tup:
        # Check if the element is not a tuple
        if not isinstance(element, tuple):
            # If not a tuple, append it to the result list
            result.append(element)
    # Convert the result list back to a tuple and return it
    return tuple(result)