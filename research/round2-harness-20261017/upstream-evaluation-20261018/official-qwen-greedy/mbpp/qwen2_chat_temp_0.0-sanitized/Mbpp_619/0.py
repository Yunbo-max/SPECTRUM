def move_num(s):
    # Split the string into parts based on numbers
    parts = s.split('1')
    # Join the parts back together, with numbers at the end
    return ''.join(parts)