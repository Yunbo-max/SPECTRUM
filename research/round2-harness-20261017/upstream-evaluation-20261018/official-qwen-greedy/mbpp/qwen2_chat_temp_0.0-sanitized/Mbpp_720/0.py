def add_dict_to_tuple(tup, dict):
    # Convert the tuple to a list to allow modification
    list_tup = list(tup)
    # Append the dictionary to the list
    list_tup.append(dict)
    # Convert the list back to a tuple
    return tuple(list_tup)