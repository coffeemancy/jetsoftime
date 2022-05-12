import typing

DataPoint = typing.Tuple[float, float]

# Quick and Dirty.
class PiecewiseLinear:

    def __init__(self, *args: DataPoint):
        self.points = list(args)

    def __call__(self, in_val: float) -> float:
        for ind, point in enumerate(self.points):
            if point[0] > in_val:
                if ind == 0:
                    return point[0]
                else:
                    x0 = self.points[ind-1][0]
                    x1 = point[0]

                    t = (in_val-x0)/(x1-x0)

                    y0 = self.points[ind-1][1]
                    y1 = point[1]
                    return y0 + t*(y1-y0)

        return self.points[-1][1]

    def add_point(self, new_x: float, new_y: float):
        has_inserted = False

        for ind, point in enumerate(self.points):
            if point[0] == new_x:
                self.points[ind] = new_y
                has_inserted = True
                break
            elif point[0] > new_x:
                self.points.insert(ind, (new_x, new_y))
                has_inserted = True
                break

        if not has_inserted:
            self.points.append((new_x, new_y))
