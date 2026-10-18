def find_length(binary_string):
    max_diff = 0
    current_diff = 0
    zero_count = 0
    one_count = 0
    
    for char in binary_string:
        if char == '0':
            zero_count += 1
            one_count = 0
        else:
            one_count += 1
            zero_count = 0
        
        current_diff = max(zero_count, one_count)
        max_diff = max(max_diff, current_diff)
    
    return max_diff