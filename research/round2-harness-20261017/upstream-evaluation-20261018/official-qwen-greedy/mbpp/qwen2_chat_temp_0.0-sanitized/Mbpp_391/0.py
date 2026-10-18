def convert_list_dictionary(keys, values):
    # Create an empty dictionary
    result = {}
    # Iterate over the keys and values simultaneously
    for key, value in zip(keys, values):
        # Create a nested dictionary with the key as the outer key and the value as the inner dictionary
        result[key] = {key: value}
    # Return the resulting dictionary
    return result