def sort_matrix(matrix):
    # Sort the matrix based on the sum of its rows
    matrix.sort(key=sum)
    return matrix