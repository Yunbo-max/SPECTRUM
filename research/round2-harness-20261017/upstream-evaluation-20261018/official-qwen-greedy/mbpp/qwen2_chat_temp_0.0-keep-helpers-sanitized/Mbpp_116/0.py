def tuple_to_int(tup):
    # Convert each integer in the tuple to a string and concatenate them
    result = ''.join(map(str, tup))
    # Convert the concatenated string back to an integer
    return int(result)