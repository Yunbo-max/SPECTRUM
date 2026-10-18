def check_type(tup):
    # Check if the tuple is empty
    if not tup:
        return True
    # Get the data type of the first element
    first_type = type(tup[0])
    # Check if all elements in the tuple have the same data type
    for element in tup:
        if type(element) != first_type:
            return False
    return True