def subject_marks(subject_marks):
    # Sort the list of tuples based on the second element of each tuple
    sorted_subject_marks = sorted(subject_marks, key=lambda x: x[1])
    return sorted_subject_marks