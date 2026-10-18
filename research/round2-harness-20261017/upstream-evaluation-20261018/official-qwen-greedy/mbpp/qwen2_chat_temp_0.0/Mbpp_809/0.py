def check_smaller(tup1, tup2):
    # Iterate through the elements of both tuples
    for i in range(len(tup1)):
        # Check if the element in the first tuple is smaller than the corresponding element in the second tuple
        if tup1[i] >= tup2[i]:
            return False
    return True