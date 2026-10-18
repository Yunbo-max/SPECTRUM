def find_Rotations(s):
    # Check if the string is empty or has only one character
    if len(s) <= 1:
        return 0
    
    # Concatenate the string with itself
    doubled_string = s + s
    
    # Find the index of the original string in the doubled string
    index = doubled_string.find(s)
    
    # If the index is not -1, it means the string is a rotation
    if index != -1:
        # Calculate the number of rotations
        rotations = index // len(s)
        return rotations
    else:
        # If the index is -1, the string is not a rotation
        return 0