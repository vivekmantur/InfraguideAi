def select_vm_size(
    cpu: int,
    memory: int
) -> str:

    #
    # Small workload
    #
    if cpu <= 2 and memory <= 8:
        return "Standard_B2s"

    #
    # Medium workload
    #
    if cpu <= 4 and memory <= 16:
        return "Standard_D4s_v5"

    #
    # Large workload
    #
    if cpu <= 8 and memory <= 32:
        return "Standard_D8s_v5"

    #
    # Very large workload
    #
    return "Standard_D16s_v5"