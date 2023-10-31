import math
import numpy as np
import numba
from numba import cuda
from numba import prange


def get_nearest_point_on_line(s1, s2, p, tol=1e-3):
    """Compute the nearest point on a line described by s1 and s2 to p

    Note that a point on the line can be parametrized by
        s(t) = s1 + t(s2 - s1).
    s(t) is on the line segment between s1 and s2 iff t \in [0, 1].

    The point on the line closest to p is s(t*) where
        t* = <p-s1, s2-s1> / ||s2 - s1||^2

    @return (s*, t*) where s* = s(t*)
    """
    ls = s2 - s1  # The line segment from s1 to s2
    len_ls2 = np.dot(ls, ls)  # the squared length of ls

    # If the line segment is too short, just return 0
    if len_ls2 < tol:
        return (s1, 0)

    tstar = np.dot(p - s1, ls) / len_ls2
    if tstar <= tol:
        return (s1, 0)
    if tstar >= 1 - tol:
        return (s2, 1)

    return (s1 + tstar * ls, tstar)


def get_euclidean_distance(s1, s2):
    """Compute the norm ||s2 - s1||"""
    # ls = s2 - s1
    return np.linalg.norm(s2 - s1) # math.sqrt(np.dot(ls, ls))

# @cuda.jit
# def get_euclidean_distance_gpu(s1, s2, out):
#     """Compute the norm ||s2 - s1||"""
#     # ls = s2 - s1
#     idx = cuda.grid(1)          
    
#     # out[idx] = np.linalg.norm(s2 - s1[idx])
#     out[idx] = ((s2 - s1[idx])**2).sum()
#     # return np.linalg.norm(s2 - s1) # math.sqrt(np.dot(ls, ls))
    
# @cuda.jit
# def get_euclidean_distance_gpu(x, y, out):
#     """Euclidean square distance matrix using loops
#     and the `numpy.dot` operation
#     """
#     idx = cuda.grid(1)
#     # dist = np.zeros(num_samples)
#     for i in numba.prange(num_samples):
#         out[idx] = ((x[i] - y)**2).sum()
#     return dist


# @numba.njit(fastmath=True, parallel=True)
# def numba_dist5(a, b):
#     dist = np.zeros(a.shape[0])
#     for r in prange(a.shape[0]):
#         d = 0
#         for c in range(a.shape[1]):
#             d += (b[c] - a[r, c])**2
#         dist[r] = d
#     return dist

@cuda.jit()
def get_euclidean_distance_gpu(a, b, out):
    idx = cuda.grid(1)
    d1 = (b[0] - a[idx, 0])**2
    d2 = (b[1] - a[idx, 1])**2
    out[idx] = math.sqrt(d1 + d2)
    

# @numba.njit(fastmath=True, parallel=True)
# def numba_dist5(a, b):
#     dist = np.zeros(a.shape[0])
#     for r in prange(a.shape[0]):
#         dist[r] = (b[0] - a[r,0])**2
#     return dist

def is_inside_circle(c, r, p):
    """Return whether point p is inside a circle with radius r, centered at c"""
    return (p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 <= r ** 2
