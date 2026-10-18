def is_sublist(main_list, sub_list):
    # Check if the sub_list is empty
    if not sub_list:
        return True
    # Iterate through the main_list to find the sub_list
    for i in range(len(main_list) - len(sub_list) + 1):
        # Check if the current slice of main_list matches the sub_list
        if main_list[i:i+len(sub_list)] == sub_list:
            return True
    # If no match is found, return False
    return False