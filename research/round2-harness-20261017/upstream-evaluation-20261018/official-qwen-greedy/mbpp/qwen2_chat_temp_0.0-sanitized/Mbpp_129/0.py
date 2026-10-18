def magic_square_test(matrix):
    # Check if the matrix is a square
    if len(matrix) != len(matrix[0]):
        return False
    
    # Calculate the sum of the first row
    sum_first_row = sum(matrix[0])
    
    # Check if all rows have the same sum
    for row in matrix:
        if sum(row) != sum_first_row:
            return False
    
    # Check if all columns have the same sum
    for col in range(len(matrix)):
        col_sum = sum(matrix[row][col] for row in range(len(matrix)))
        if col_sum != sum_first_row:
            return False
    
    # Check if the main diagonal has the same sum
    main_diag_sum = sum(matrix[i][i] for i in range(len(matrix)))
    if main_diag_sum != sum_first_row:
        return False
    
    # Check if the secondary diagonal has the same sum
    secondary_diag_sum = sum(matrix[i][len(matrix)-1-i] for i in range(len(matrix)))
    if secondary_diag_sum != sum_first_row:
        return False
    
    return True