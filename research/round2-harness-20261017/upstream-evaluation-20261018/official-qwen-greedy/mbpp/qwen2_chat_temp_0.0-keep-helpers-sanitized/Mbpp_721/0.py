def maxAverageOfPath(matrix):
    # Initialize the number of rows and columns in the matrix
    rows, cols = len(matrix), len(matrix[0])
    
    # Initialize the maximum average to negative infinity
    max_avg = float('-inf')
    
    # Iterate through each cell in the matrix
    for i in range(rows):
        for j in range(cols):
            # Initialize the current sum of the path
            current_sum = matrix[i][j]
            
            # Iterate through all possible paths starting from the current cell
            for k in range(i, rows):
                for l in range(j, cols):
                    # Add the cost of the current cell to the current sum
                    current_sum += matrix[k][l]
                    
                    # Calculate the average of the current path
                    avg = current_sum / (k - i + 1) / (l - j + 1)
                    
                    # Update the maximum average if the current average is greater
                    max_avg = max(max_avg, avg)
    
    # Return the maximum average found
    return max_avg