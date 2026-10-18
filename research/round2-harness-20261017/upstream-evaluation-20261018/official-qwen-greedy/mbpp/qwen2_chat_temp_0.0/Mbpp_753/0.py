def min_k(records, k):
    # Sort the records based on the second element of each tuple in ascending order
    sorted_records = sorted(records, key=lambda x: x[1])
    # Return the first k records from the sorted list
    return sorted_records[:k]