from typing import Self

class VectorClock():
    def __init__(self, n=1, entries=None):
        # TODO: Init vector clock with num and integer entries, you might want to create a copy of the entries
        if entries != None:
            self.clock = list(entries)
        else:
            self.clock = [0] * n

    # TODO: Increment the respective clock index when an event occurs on server i
    def increment(self, i):
        if i < len(self.clock):
            self.clock[i] += 1 
        else:
            while len(self.clock) <= i:
                self.clock.append(0)
            self.clock[i] += 1

    # TODO: Update our own entries based on the other clock
    def update(self, other: Self):
        i = 0
        while i < max(len(self.clock), len(other.clock)):
            if len(self.clock) <= i:
                self.clock.append(other.clock[i])
            elif len(other.clock) <= i:
                pass
            else:
                if self.clock[i] < other.clock[i]:
                    self.clock[i] = other.clock[i]
            i += 1

    # Todo: Implement me
    def from_list(entries : list) -> Self:
        return VectorClock(entries=entries)

    # Todo: Implement me
    def to_list(self) -> list:
        return list(self.clock)

    # Todo: Implement me
    def is_parallel(self, other):
        return not (self < other) and not (other < self) and self.clock != other.clock

    # Todo: Implement me, check if our clock is strictly smaller than the other one!
    def __lt__(self, other):
        equal = True
        i = 0
        while i <  max(len(self.clock), len(other.clock)):
            if i >= len(self.clock):
                if other.clock[i] > 0:
                    equal = False
            elif i >= len(other.clock):
                if self.clock[i] > 0:
                    return False
            elif self.clock[i] > other.clock[i]:
                return False
            elif self.clock[i] < other.clock[i]:
                equal = False
            i += 1
        return not equal

    # a simple copy function for now
    def copy(self : Self) -> Self:
        return VectorClock.from_list(self.to_list())


if __name__ == "__main__":
    # you can use test.py or you can test your code here, just execute it using python3 vector_clock.py then
    # please extend it to match all the requirements of vector clocks ;)

    c0 = VectorClock(n=1, entries=[0])

    c1 = c0.copy()
    c1.increment(0)

    c2 = c1.copy()
    c2.update(c0)

    assert c0 < c1
    assert c0 < c2
    assert not (c1 < c2)
