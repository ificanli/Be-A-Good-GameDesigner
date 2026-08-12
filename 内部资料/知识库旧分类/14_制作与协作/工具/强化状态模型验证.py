"""有限状态强化模型验证工具。

无第三方依赖。修改 P、COST、START、TARGET 后运行：
    python 14_制作与协作/工具/强化状态模型验证.py

P[i][j]：当前状态 i 一次强化后进入状态 j 的概率。
COST[i]：在状态 i 发起一次强化的成本。
TARGET 必须在 P 中设为吸收态。
"""

P = [
    [.25, .75, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, .40, .60, 0, 0, 0, 0, 0, 0, 0],
    [0, .50, 0, .50, 0, 0, 0, 0, 0, 0],
    [0, .55, 0, 0, .45, 0, 0, 0, 0, 0],
    [0, .85, 0, 0, 0, .15, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, .80, .20, 0, 0, 0],
    [0, 0, 0, 0, 0, .90, 0, .10, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, .99, .01, 0],
    [0, 0, 0, 0, 0, 0, 0, .98, 0, .02],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
]
COST = [1, 1, 2, 2, 2, 3, 3, 4, 4, 0]
START = 0
TARGET = 9
QUANTILES = (.50, .90, .95, .99)
MAX_STEPS = 300_000


def solve(matrix, vector):
    """使用带主元选择的高斯消元解线性方程组。"""
    a = [row[:] + [value] for row, value in zip(matrix, vector)]
    size = len(a)
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(a[row][column]))
        if abs(a[pivot][column]) < 1e-12:
            raise ValueError("矩阵不可逆：请检查目标是否可达、是否正确设为吸收态")
        a[column], a[pivot] = a[pivot], a[column]
        divisor = a[column][column]
        for index in range(column, size + 1):
            a[column][index] /= divisor
        for row in range(size):
            if row == column:
                continue
            factor = a[row][column]
            for index in range(column, size + 1):
                a[row][index] -= factor * a[column][index]
    return [row[-1] for row in a]


def validate():
    size = len(P)
    if any(len(row) != size for row in P):
        raise ValueError("P 必须是方阵")
    if len(COST) != size:
        raise ValueError("COST 长度必须与状态数一致")
    for index, row in enumerate(P):
        if any(value < 0 for value in row):
            raise ValueError(f"第 {index + 1} 行存在负概率")
        if abs(sum(row) - 1) > 1e-9:
            raise ValueError(f"第 {index + 1} 行概率和不是 1")
    expected_target_row = [0.0] * size
    expected_target_row[TARGET] = 1.0
    if any(abs(a - b) > 1e-9 for a, b in zip(P[TARGET], expected_target_row)):
        raise ValueError("TARGET 行必须是吸收态")


def transient_model():
    transient = [state for state in range(len(P)) if state != TARGET]
    position = {state: index for index, state in enumerate(transient)}
    q = [[P[i][j] for j in transient] for i in transient]
    a = [[float(i == j) - q[i][j] for j in range(len(q))] for i in range(len(q))]
    attempts = solve(a, [1.0] * len(q))
    costs = solve(a, [COST[state] for state in transient])
    return transient, q, attempts[position[START]], costs[position[START]]


def attempt_quantiles(transient, q):
    position = {state: index for index, state in enumerate(transient)}
    distribution = [0.0] * len(transient)
    distribution[position[START]] = 1.0
    result = {quantile: None for quantile in QUANTILES}
    for step in range(1, MAX_STEPS + 1):
        distribution = [
            sum(distribution[i] * q[i][j] for i in range(len(q)))
            for j in range(len(q))
        ]
        reached = 1.0 - sum(distribution)
        for quantile in result:
            if result[quantile] is None and reached >= quantile:
                result[quantile] = step
        if all(value is not None for value in result.values()):
            return result
    raise RuntimeError("MAX_STEPS 内未找到全部分位数；规则可能有极长尾或目标并非必达")


def main():
    validate()
    transient, q, expected_attempts, expected_cost = transient_model()
    quantiles = attempt_quantiles(transient, q)
    print(f"期望尝试次数：{expected_attempts:.6f}")
    print(f"期望总成本：{expected_cost:.6f}")
    for quantile, steps in quantiles.items():
        print(f"尝试次数 P{int(quantile * 100)}：{steps}")


if __name__ == "__main__":
    main()
