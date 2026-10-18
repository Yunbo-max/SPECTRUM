def sub_list(list1, list2):
    # Use list comprehension to subtract corresponding elements of the lists
    result = [a - b for a, b in zip(list1, list2)]
    return result