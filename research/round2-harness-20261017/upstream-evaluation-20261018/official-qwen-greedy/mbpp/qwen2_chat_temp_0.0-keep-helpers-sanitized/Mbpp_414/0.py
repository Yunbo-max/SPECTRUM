def overlapping(seq1, seq2):
    # Check if any value in seq1 exists in seq2
    for item in seq1:
        if item in seq2:
            return True
    return False