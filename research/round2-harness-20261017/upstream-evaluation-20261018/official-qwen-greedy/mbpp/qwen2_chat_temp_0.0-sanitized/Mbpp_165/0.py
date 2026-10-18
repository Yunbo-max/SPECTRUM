def count_char_position(s):
    count = 0
    for i, char in enumerate(s):
        if char.lower() == chr(ord('a') + i):
            count += 1
    return count