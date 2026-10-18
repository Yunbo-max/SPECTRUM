def check_Consecutive(lst):
    # Check if the list is empty or contains only one element
    if len(lst) <= 1:
        return True
    
    # Iterate through the list to check for consecutive numbers
    for i in range(len(lst) - 1):
        if lst[i] + 1 != lst[i + 1]:
            return False
    
    return True