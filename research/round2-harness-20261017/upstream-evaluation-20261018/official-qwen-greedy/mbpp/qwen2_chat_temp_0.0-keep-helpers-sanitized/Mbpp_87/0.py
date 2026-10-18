def merge_dictionaries_three(dict1, dict2, dict3):
    # Merge the dictionaries using the update() method
    dict1.update(dict2)
    dict1.update(dict3)
    return dict1