def surface_Area(base_edge, height):
    # Calculate the area of the base
    base_area = base_edge ** 2
    # Calculate the slant height of the pyramid
    slant_height = (base_edge ** 2 + height ** 2) ** 0.5
    # Calculate the lateral surface area
    lateral_surface_area = 2 * base_edge * slant_height
    # Calculate the total surface area
    total_surface_area = base_area + lateral_surface_area
    return total_surface_area