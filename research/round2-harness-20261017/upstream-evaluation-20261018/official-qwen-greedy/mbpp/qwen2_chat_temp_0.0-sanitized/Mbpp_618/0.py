def div_list(list1, list2):
    # Check if the lists are of the same length
    if len(list1) != len(list2):
        raise ValueError("Lists must be of the same length")
    
    # Perform element-wise division
    result = [a / b for a, b in zip(list1, list2)]
    
    return result