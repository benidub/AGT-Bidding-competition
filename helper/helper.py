import random


class Item:
    def __init__(self, name: str, value: float):
        self.name = name
        self.value = value


class Classification:
    def __init__(self, high: list[Item], low: list[Item], wildcard: list[Item]):
        assert len(high) == 6
        assert len(low) == 4
        assert len(wildcard) == 10
        self.high = high
        self.low = low
        self.wildcard = wildcard

    def difference(self, other: 'Classification') -> int:
        correct = 0
        for item in self.high:
            if item in other.high:
                correct += 1
        for item in self.low:
            if item in other.low:
                correct += 1
        for item in self.wildcard:
            if item in other.wildcard:
                correct += 1
        return correct

    def __repr__(self):
        return f"Classification(high={[(item.name, item.value) for item in self.high]}, low={[(item.name, item.value) for item in self.low]}, wildcard={[(item.name, item.value) for item in self.wildcard]})"


class AbstractClassifier:
    def classify(self, items: list[Item]) -> Classification:
        raise NotImplementedError


class BayesOptimalClassifier(AbstractClassifier):
    def classify(self, items: list[Item]) -> Classification:
        high = [(i, x) for i, x in enumerate(items) if x.value > 10]
        low = [(i, x) for i, x in enumerate(items) if x.value <= 10]
        score_A = [(i, (1 / 10) / (1 / 19)) for i, _ in high]
        score_B = [(i, (1 / 9) / (1 / 19)) for i, _ in low]
        score_A.sort(key=lambda t: t[1], reverse=True)
        score_B.sort(key=lambda t: t[1], reverse=True)

        high_items = []
        low_items = []
        wildcard_items = []

        for i, _ in score_A[:6]:
            high_items.append(items[i])
        for i, _ in score_B[:4]:
            low_items.append(items[i])
        used_indices = {i for i, _ in score_A[:6]} | {i for i, _ in score_B[:4]}
        for i in range(len(items)):
            if i not in used_indices:
                wildcard_items.append(items[i])
        return Classification(high=high_items, low=low_items, wildcard=wildcard_items)


class NaiveOptimalClassifier(AbstractClassifier):
    def classify(self, items: list[Item]) -> Classification:
        sorted_items = sorted(items, key=lambda item: item.value)
        low = sorted_items[:4]
        high = sorted_items[-6:]
        wildcard = sorted_items[4:-6]
        return Classification(high=high, low=low, wildcard=wildcard)


def generate_classification() -> Classification:
    # 6 numbers from U[10,20], 4 numbers from U[1,10], 10 numbers from U[1,20]
    high = [Item(name=f"H{i}", value=random.uniform(10, 20)) for i in range(6)]
    low = [Item(name=f"L{i}", value=random.uniform(1, 10)) for i in range(4)]
    wildcard = [Item(name=f"W{i}", value=random.uniform(1, 20)) for i in range(10)]
    return Classification(high=high, low=low, wildcard=wildcard)


def test_bayes_optimal_global():
    true_classification = generate_classification()
    classifier = NaiveOptimalClassifier()
    predicted_classification = classifier.classify(
        true_classification.high + true_classification.low + true_classification.wildcard
    )
    return true_classification.difference(predicted_classification)


def main(start, end, limit):
    total = 0
    for i in range(limit):
        total += test_bayes_optimal_global()
    print("Average correct classifications:", total / limit)


def get_maximum_of_uniform_distribution(start: int, end: int, samples: int) -> float:
    max_value = float('-inf')
    for _ in range(samples):
        value = random.uniform(start, end)
        if value > max_value:
            max_value = value
    return max_value


def calculate_expected_maximum(start: int, end: int, samples: int, trials: int) -> float:
    total_max = 0.0
    for _ in range(trials):
        total_max += get_maximum_of_uniform_distribution(start, end, samples)
    return total_max / trials


if __name__ == '__main__':
    # print(calculate_expected_maximum(10, 20, 5, 1_000_000))
    print(main(1, 20, 10 ** 4))
