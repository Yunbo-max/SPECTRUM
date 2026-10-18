def find_Average_Of_Cube(n):
    # Calculate the sum of cubes of first n natural numbers
    sum_of_cubes = sum([i**3 for i in range(1, n+1)])
    # Calculate the average of the sum of cubes
    average = sum_of_cubes / n
    return average