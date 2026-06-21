"""最小二乘求解 - 基于正规方程和高斯消元"""

from typing import List, Tuple


def mat_mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    """矩阵乘法 A * B"""
    m = len(A)
    n = len(B[0])
    k = len(B)
    result = [[0.0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            s = 0.0
            for p in range(k):
                s += A[i][p] * B[p][j]
            result[i][j] = s
    return result


def mat_transpose(A: List[List[float]]) -> List[List[float]]:
    """矩阵转置"""
    m = len(A)
    n = len(A[0])
    return [[A[i][j] for i in range(m)] for j in range(n)]


def mat_vec_mul(A: List[List[float]], x: List[float]) -> List[float]:
    """矩阵乘向量 A * x"""
    m = len(A)
    n = len(A[0])
    result = [0.0] * m
    for i in range(m):
        s = 0.0
        for j in range(n):
            s += A[i][j] * x[j]
        result[i] = s
    return result


def gaussian_elimination(A: List[List[float]], b: List[float]) -> List[float]:
    """
    高斯消元求解线性方程组 Ax = b
    使用部分选主元提高数值稳定性
    """
    n = len(A)
    aug = [row[:] + [b[i]] for i, row in enumerate(A)]

    for col in range(n):
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row
        if max_row != col:
            aug[col], aug[max_row] = aug[max_row], aug[col]

        pivot = aug[col][col]
        if abs(pivot) < 1e-12:
            raise ValueError("矩阵奇异或接近奇异，无法求解")

        for row in range(col + 1, n):
            factor = aug[row][col] / pivot
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]

    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = aug[i][n]
        for j in range(i + 1, n):
            s -= aug[i][j] * x[j]
        x[i] = s / aug[i][i]

    return x


def least_squares(A: List[List[float]], b: List[float]) -> Tuple[List[float], float]:
    """
    最小二乘求解 min ||Ax - b||^2
    使用正规方程法：A^T A x = A^T b

    返回: (解向量 x, 残差平方和)
    """
    m = len(A)
    n = len(A[0])

    if m < n:
        raise ValueError(
            f"观测点数量 ({m}) 少于待求参数数量 ({n})，无法唯一确定解"
        )

    At = mat_transpose(A)
    AtA = mat_mul(At, A)
    Atb = mat_vec_mul(At, b)

    x = gaussian_elimination(AtA, Atb)

    Ax = mat_vec_mul(A, x)
    residual_sum = sum((b[i] - Ax[i]) ** 2 for i in range(m))

    return x, residual_sum
