def left_rotate(num, d):
    """
    Rotate left bits by d bits a given number. We assume that the number is 32 bit.
    """
    # Shift the number left by d bits
    rotated_num = (num << d) & 0xFFFFFFFF
    return rotated_num