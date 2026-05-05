#Projekt/src , Projekt/data , Projekt/docs

from pathlib import Path



first = Path("Projekt")

first.mkdir()

folders_names = ["src", "data", "docs"]

for i in folders_names:
    
    path = Path(f"Projekt/{i}")
    path.mkdir()