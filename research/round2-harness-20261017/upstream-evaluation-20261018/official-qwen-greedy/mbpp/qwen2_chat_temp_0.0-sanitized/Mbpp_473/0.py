def tuple_intersection(tup1, tup2):
    # Convert tuples to sets to remove duplicates and perform intersection
    set1 = set(tup1)
    set2 = set(tup2)
    # Return the intersection of the two sets
    return set1.intersection(set2)