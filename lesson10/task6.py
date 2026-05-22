class Wektor2D:

    def __init__(self, x: float, y: float):

        self.x = x
        self.y = y

    def __add__(self, other):

        if isinstance(other, Wektor2D):

            return Wektor2D(self.x + other.x, self.y + other.y)
        
        return NotImplemented

    def __sub__(self, other):

        if isinstance(other, Wektor2D):

            return Wektor2D(self.x - other.x, self.y - other.y)
        
        return NotImplemented

    def __eq__(self, other):

        if isinstance(other, Wektor2D):

            return self.x == other.x and self.y == other.y
        
        return NotImplemented

    def __str__(self):
        
        return f"({self.x}, {self.y})"


vec = Wektor2D(-12.45, 20.78)
vec2 = Wektor2D(23.90, 123.90)

print(vec + vec2)
print(vec - vec2)
print(vec == vec2)