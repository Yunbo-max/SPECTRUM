def split_two_parts(lst, L):
    # Split the list into two parts
    part1 = lst[:L]
    part2 = lst[L:]
    # Return the resulting lists in a tuple
    return (part1, part2)