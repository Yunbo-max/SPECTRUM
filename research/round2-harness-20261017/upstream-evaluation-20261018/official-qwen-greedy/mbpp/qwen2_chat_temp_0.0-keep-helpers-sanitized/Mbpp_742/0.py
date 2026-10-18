import math
def area_tetrahedron(side_length):
    # Calculate the area of a triangle using Heron's formula
    area_triangle = math.sqrt(3) * (side_length ** 2) / 4
    # Calculate the area of the tetrahedron by summing the areas of the four triangular faces
    area_tetrahedron = 4 * area_triangle
    return area_tetrahedron