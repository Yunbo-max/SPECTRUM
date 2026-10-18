def difference(n):
    # Calculate the sum of cubes of the first n natural numbers
    sum_of_cubes = sum([i**3 for i in range(1, n+1)])
    # Calculate the sum of the first n natural numbers
    sum_of_natural_numbers = sum(range(1, n+1))
    # Return the difference between the two sums
    return sum_of_cubes - sum_of_natural_numbers