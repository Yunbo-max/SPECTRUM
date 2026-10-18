def tuple_to_dict(tup):
    # Initialize an empty dictionary
    result_dict = {}
    # Iterate over the tuple using enumerate to get both index and value
    for index, value in enumerate(tup):
        # Assign the value to the key at the current index in the dictionary
        result_dict[index] = value
    # Return the resulting dictionary
    return result_dict