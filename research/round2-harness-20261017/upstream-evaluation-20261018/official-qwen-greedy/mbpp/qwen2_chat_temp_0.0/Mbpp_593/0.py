def removezero_ip(ip):
    # Split the IP address into its components
    components = ip.split('.')
    
    # Remove leading zeroes from each component
    components = [str(int(component)) for component in components]
    
    # Join the components back into a single string
    return '.'.join(components)