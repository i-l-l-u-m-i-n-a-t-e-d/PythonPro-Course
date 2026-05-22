class Punkt:
    
    def __init__(self, x: float, y: float):
        
        self.x = x
        self.y = y
        
    
    def __str__(self):
        
        return f"({self.x}, {self.y})"
    

punkt = Punkt(123.23, 456.90)

print(punkt)
        
        