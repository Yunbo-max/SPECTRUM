def index_minimum(tuples_list):
    # Find the tuple with the smallest second value
    min_tuple = min(tuples_list, key=lambda x: x[1])
    # Return the first value of the tuple with the smallest second value
    return min_tuple[0]