def select_vm_size(
    cpu: int,
    memory: int
) -> str:

    """Select an Azure VM size for CPU and memory requirements.
    
    Args:
        cpu: cpu value.
        memory: memory value.
    
    Returns:
        Select vm size result.
    """
    if cpu <= 2 and memory <= 8:
        return "Standard_B2s"
    if cpu <= 4 and memory <= 16:
        return "Standard_D4s_v5"
    if cpu <= 8 and memory <= 32:
        return "Standard_D8s_v5"
    return "Standard_D16s_v5"
