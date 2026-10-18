def larg_nnum(l, n):
    # Sort the list in descending order
    l.sort(reverse=True)
    # Return the first n elements of the sorted list
    return l[:n]