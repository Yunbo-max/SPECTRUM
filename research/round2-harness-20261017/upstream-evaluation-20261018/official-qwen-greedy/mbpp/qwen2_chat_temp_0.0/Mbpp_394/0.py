def check_distinct(tup):
    # Convert the tuple to a set to remove duplicates
    unique_elements = set(tup)
    # Compare the length of the set with the original tuple
    return len(unique_elements) == len(tup)