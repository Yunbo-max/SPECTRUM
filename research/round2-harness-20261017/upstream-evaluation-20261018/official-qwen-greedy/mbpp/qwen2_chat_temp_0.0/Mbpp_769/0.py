def Diff(list1, list2):
    # Use set difference to find elements in list1 that are not in list2
    return list(set(list1) - set(list2))