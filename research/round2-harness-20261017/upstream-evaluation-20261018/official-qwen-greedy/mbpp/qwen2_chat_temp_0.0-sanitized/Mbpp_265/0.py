def list_split(lst, n):
    """
    Splits a list into sublists of length n, returning a list of these sublists.
    
    Parameters:
    lst (list): The list to be split.
    n (int): The length of each sublist.
    
    Returns:
    list: A list of sublists, each containing n elements from the original list.
    """
    return [lst[i:i+n] for i in range(0, len(lst), n)]