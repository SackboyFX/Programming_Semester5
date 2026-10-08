import ifcopenshell
import pandas as pd

model = ifcopenshell.open(r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\ARC_Modell_NEST_230328.ifc")

for wall_type in model.by_type("IfcWallType"):
    print("The wall type element is", wall_type)
    print("The name of the wall type is", wall_type.Name)