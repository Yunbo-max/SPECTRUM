def get_equal(tuples_list):
    # Check if the list is empty
    if not tuples_list:
        return True
    
    # Get the length of the first tuple
    first_tuple_length = len(tuples_list[0])
    
    # Check if all tuples have the same length
    for tuple_ in tuples_list:
        if len(tuple_) != first_tuple_length:
            return False
    
    return True