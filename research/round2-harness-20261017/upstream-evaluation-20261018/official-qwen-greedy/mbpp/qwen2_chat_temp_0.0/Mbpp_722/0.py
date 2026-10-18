def filter_data(data, min_height, min_weight):
    # Initialize an empty dictionary to store filtered students
    filtered_students = {}
    # Iterate over each student in the input dictionary
    for student, (height, weight) in data.items():
        # Check if the student's height and weight are above the minimum
        if height > min_height and weight > min_weight:
            # If so, add the student to the filtered dictionary
            filtered_students[student] = (height, weight)
    # Return the filtered dictionary
    return filtered_students