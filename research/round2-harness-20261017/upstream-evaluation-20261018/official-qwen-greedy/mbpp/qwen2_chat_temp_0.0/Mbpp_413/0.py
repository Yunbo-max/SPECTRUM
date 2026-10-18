def extract_nth_element(tuples_list, n):
    # Extract the nth element from each tuple in the list
    result = [tup[n] for tup in tuples_list]
    return result