def remove_dirty_chars(s1, s2):
    # Convert both strings to sets to remove duplicates and perform intersection
    dirty_chars = set(s2)
    # Use list comprehension to filter out characters from s1 that are in dirty_chars
    result = ''.join([char for char in s1 if char not in dirty_chars])
    return result