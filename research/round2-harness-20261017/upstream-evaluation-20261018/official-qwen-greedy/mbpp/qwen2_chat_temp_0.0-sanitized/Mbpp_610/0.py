def remove_kth_element(lst, k):
    # Remove the k'th element from the list
    return lst[:k] + lst[k+1:]