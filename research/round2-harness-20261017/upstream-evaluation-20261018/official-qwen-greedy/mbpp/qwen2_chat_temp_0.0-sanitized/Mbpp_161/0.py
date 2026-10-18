def remove_elements(main_list, elements_to_remove):
    # Use list comprehension to filter out elements present in elements_to_remove
    filtered_list = [element for element in main_list if element not in elements_to_remove]
    return filtered_list