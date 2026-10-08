# IFC Open Shell Documentation: https://docs.ifcopenshell.org/ifcopenshell-python/hello_world.html
#This is a test 

import ifcopenshell
import pandas as pd

model = ifcopenshell.open(r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\ARC_Modell_NEST_230328.ifc")

print(model.schema)
print(model.by_id(1))
print(model.by_guid('0KJ$FDU6nM29SMLWGbbTF3'))
walls = model.by_type('ifcwall')
print('The first wall is', walls[0])

print(walls[0].is_a())
print(walls[0].is_a('IFCWall'))
print('The wall ID is', walls[0].id())

print(walls[0])

for i in range(0,7):
    print(walls[0][i])

print()

print(walls[0].get_info())

#df = pd.DataFrame(walls) 
#print(df)

print()

print('The name of this wall is', walls[5].Name)

import ifcopenshell.util
import ifcopenshell.util.element

print()

#print('The PSETS are', ifcopenshell.util.element.get_psets(walls[0]))

#print('The wall is defined by', walls[0].IsDefinedBy)

#To continue, continue IFC documentary: 'Perhaps we want to see all elements which are referencing our wall?' till the end, then look at Code Examples, then see the PDF from school.

#print(model.traverse(walls[0]))

wallnew = walls[0]

wallnew.Name = "Mike Khayat is a Wall"

print(wallnew.Name)

model.write(r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\Modified_IFC.ifc")