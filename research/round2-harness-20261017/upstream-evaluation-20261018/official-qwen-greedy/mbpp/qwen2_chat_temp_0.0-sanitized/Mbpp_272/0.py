def rear_extract(tuples_list):
    # Extract the rear element of each tuple using list comprehension
    rear_elements = [tup[-1] for tup in tuples_list]
    return rear_elements