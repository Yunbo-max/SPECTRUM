def drop_empty(input_dict):
    # Using dictionary comprehension to filter out None values
    return {key: value for key, value in input_dict.items() if value is not None}