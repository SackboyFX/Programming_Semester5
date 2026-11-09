# IFC Open Shell Documentation: https://docs.ifcopenshell.org/ifcopenshell-python/hello_world.html
#This is a test 

import ifcopenshell
import pandas as pd
import ifcopenshell.util
import ifcopenshell.util.element

model = ifcopenshell.open(r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\25.011_GoBau.ifc")

road = model.by_type('IfcCourse')

print(ifcopenshell.util.element.get_psets(road[0])["GoBau_Menge"]["Volumen (m3)"])
print(type(ifcopenshell.util.element.get_psets(road[0])["GoBau_Menge"]["Volumen (m3)"]))

site = [x for x in model.by_type('IfcSite') if x.Name == '03 Neu'][0]
inside = ifcopenshell.util.element.get_decomposition(site) #This returns to me all the elements under the site. 
#Get_Decomposition is a function that returns all the elements that are part of the decomposition of the given element. In this case, it returns all the elements that are part of the site with the name '03 Neu'.  
elements = [e for e in inside if e.is_a("IfcElement")] #Returns IFCElements as a List.

kostenteilerset = {'WWZ-WV:100%', 'ZUG:100%', 'WWZ-EW:100%'}

results = []

i: ifcopenshell.entity_instance #One IFC element out of the elements list (e.g. an IfcCourse)
psets: str #The value of the Kostenteiler property, e.g. 'ZUG:100%'
for i in elements:
    try:
        #print(f'{i.Name}, {i.is_a()}')
        psets = ifcopenshell.util.element.get_psets(i)["GoBau_Ausschreibung"]["Kostenteiler"]
        if psets in kostenteilerset:
            # print(f"Kostenteiler: {psets}")
            # print()
            results.append({"GUID": i.GlobalId, "Name": i.Name, "Kostenteiler": psets, "Check": "PASS"})
        else:
            # print(f"Error >>> Kostenteiler: \"{psets}\" is not in the set")
            # print()
            results.append({"GUID": i.GlobalId, "Name": i.Name, "Kostenteiler": psets, "Check": "FAIL"})
    except KeyError:
        # print("KEYERROR: KOSTENTEILER DOESNT EXIST occurred for element")
        # print()
        results.append({"GUID": i.GlobalId, "Name": i.Name, "Kostenteiler": "NONE", "Check": "FAIL"})

print(results[0])

df = pd.DataFrame(results)
print(df)



# print(kostenteilerset)




# sites = model.by_type('IfcSite')
# print(len(sites))
# print(ifcopenshell.util.element.get_psets(sites[3]))

# print(model.schema)
# print(model.by_id(1))
# print(model.by_guid('0KJ$FDU6nM29SMLWGbbTF3'))
# walls = model.by_type('ifcwall')
# print('The first wall is', walls[0])

# print(walls[0].is_a())
# print(walls[0].is_a('IFCWall'))
# print('The wall ID is', walls[0].id())

# print(walls[0])

# for i in range(0,7):
#     print(walls[0][i])

# print()

# print(walls[0].get_info())

# #df = pd.DataFrame(walls) 
# #print(df)

# print()

# print('The name of this wall is', walls[5].Name)

# import ifcopenshell.util
# import ifcopenshell.util.element

# print()

# #print('The PSETS are', ifcopenshell.util.element.get_psets(walls[0]))

# #print('The wall is defined by', walls[0].IsDefinedBy)

# #To continue, continue IFC documentary: 'Perhaps we want to see all elements which are referencing our wall?' till the end, then look at Code Examples, then see the PDF from school.

# #print(model.traverse(walls[0]))

# wallnew = walls[0]

# wallnew.Name = "Mike Khayat is a Wall"

# print(wallnew.Name)

# model.write(r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\Modified_IFC.ifc")