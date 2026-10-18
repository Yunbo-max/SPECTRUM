def remove_Occ(s, c):
    # Remove the first occurrence of the character
    s = s.replace(c, '', 1)
    # Remove the last occurrence of the character
    s = s.replace(c, '', 1)
    return s