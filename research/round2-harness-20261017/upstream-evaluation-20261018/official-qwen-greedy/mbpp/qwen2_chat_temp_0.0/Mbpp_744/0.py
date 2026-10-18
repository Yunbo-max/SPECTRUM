def check_none(tup):
    # Iterate through each element in the tuple
    for element in tup:
        # Check if the element is None
        if element is None:
            # Return True if any None value is found
            return True
    # Return False if no None value is found
    return False