import math


def run_simulation():
    labels = []
    values = []

    for i in range(50):
        labels.append(i)
        values.append(math.sin(i * 0.2))

    return {
        "labels": labels,
        "values": values
    }
