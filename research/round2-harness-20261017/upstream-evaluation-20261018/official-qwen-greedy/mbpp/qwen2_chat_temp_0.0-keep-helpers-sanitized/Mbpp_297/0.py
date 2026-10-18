def flatten_list(nested_list):
    # Initialize an empty list to store the flattened elements
    flattened_list = []
    # Iterate through each element in the nested list
    for element in nested_list:
        # If the element is a list, recursively flatten it
        if isinstance(element, list):
            flattened_list.extend(flatten_list(element))
        # If the element is not a list, append it to the flattened list
        else:
            flattened_list.append(element)
    # Return the flattened list
    return flattened_list