def unique_Element(lst):
    # Check if the length of the list is 1
    if len(lst) == 1:
        return True
    else:
        # Check if all elements in the list are the same
        return all(x == lst[0] for x in lst)