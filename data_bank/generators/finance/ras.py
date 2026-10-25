import numpy as np
import pandas as pd

def ras_fit(matrix, row_targets, col_targets, tol=1e-6, max_iter=1000, pinned_mask=None):
    """
    Biproportional fitting (RAS) of matrix to row_targets and col_targets.
    pinned_mask is boolean mask where True means the value is fixed and shouldn't be scaled.
    """
    matrix = np.array(matrix, dtype=float)
    row_targets = np.array(row_targets, dtype=float)
    col_targets = np.array(col_targets, dtype=float)
    
    if pinned_mask is None:
        pinned_mask = np.zeros_like(matrix, dtype=bool)
    else:
        pinned_mask = np.array(pinned_mask, dtype=bool)
        
    # Subtract pinned values from targets
    row_targets_adj = row_targets - np.sum(matrix * pinned_mask, axis=1)
    col_targets_adj = col_targets - np.sum(matrix * pinned_mask, axis=0)
    
    # We only scale the unpinned part
    m_unpinned = matrix.copy()
    m_unpinned[pinned_mask] = 0.0
    
    for iteration in range(max_iter):
        row_sums = np.sum(m_unpinned, axis=1)
        row_sums[row_sums == 0] = 1.0 # avoid div by zero
        r_scale = row_targets_adj / row_sums
        m_unpinned = m_unpinned * r_scale[:, np.newaxis]
        
        col_sums = np.sum(m_unpinned, axis=0)
        col_sums[col_sums == 0] = 1.0
        c_scale = col_targets_adj / col_sums
        m_unpinned = m_unpinned * c_scale[np.newaxis, :]
        
        # Check convergence
        row_err = np.max(np.abs(np.sum(m_unpinned, axis=1) - row_targets_adj))
        col_err = np.max(np.abs(np.sum(m_unpinned, axis=0) - col_targets_adj))
        if row_err < tol and col_err < tol:
            break
            
    # Recombine
    matrix_final = m_unpinned.copy()
    matrix_final[pinned_mask] = matrix[pinned_mask]
    return matrix_final
    
def largest_remainder_round(values, target_sum, precision=2):
    """Round array to a specific precision while matching target_sum exactly."""
    factor = 10**precision
    scaled = values * factor
    floored = np.floor(scaled)
    remainders = scaled - floored
    
    diff = int(round(target_sum * factor - np.sum(floored)))
    if abs(diff) > len(values) + 10:
        print(f"WARNING: huge diff = {diff} for target = {target_sum} and len = {len(values)}")

    
    if diff > 0:
        indices = np.argsort(remainders)[::-1]
        for i in range(diff):
            floored[indices[i % len(indices)]] += 1
            
    elif diff < 0:
        indices = np.argsort(remainders)
        for i in range(-diff):
            floored[indices[i % len(indices)]] -= 1
            
    return floored / factor
