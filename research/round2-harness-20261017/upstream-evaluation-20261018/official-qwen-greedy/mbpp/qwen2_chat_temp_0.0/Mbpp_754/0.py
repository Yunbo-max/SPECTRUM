def extract_index_list(l1, l2, l3):
    # Find the common elements in all three lists
    common_elements = [element for element in l1 if element in l2 and element in l3]
    return common_elements