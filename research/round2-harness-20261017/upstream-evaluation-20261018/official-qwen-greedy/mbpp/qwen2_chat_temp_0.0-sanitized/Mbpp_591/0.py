def swap_List(lst):
    # Swap the first and last elements
    lst[0], lst[-1] = lst[-1], lst[0]
    return lst