def insert_element(lst, element):
    # Initialize an empty list to store the result
    result = []
    # Iterate over each element in the input list
    for item in lst:
        # Append the element to the result list
        result.append(item)
        # Append the element to the result list again
        result.append(element)
    # Return the resulting list
    return result