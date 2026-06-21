def select_machine_type(
    cpu: int,
    memory: int
) -> dict:

    """Select a GCP machine type for CPU and memory requirements.
    
    Args:
        cpu: cpu value.
        memory: memory value.
    
    Returns:
        Select machine type result.
    """
    if cpu <= 2 and memory <= 8:
        return {
            "machine_type": "e2-medium",
            "machine_family": "E2",
            "cpu": cpu,
            "memory": memory
        }

    if cpu <= 4 and memory <= 16:
        return {
            "machine_type": "n2-standard-4",
            "machine_family": "N2",
            "cpu": cpu,
            "memory": memory
        }

    if cpu <= 8 and memory <= 32:
        return {
            "machine_type": "n2-standard-8",
            "machine_family": "N2",
            "cpu": cpu,
            "memory": memory
        }

    return {
        "machine_type": "n2-standard-16",
        "machine_family": "N2",
        "cpu": cpu,
        "memory": memory
    }