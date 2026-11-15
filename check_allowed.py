import ifcopenshell
import pandas as pd
import ifcopenshell.util
import ifcopenshell.util.element

model = ifcopenshell.open(r"C:\Users\mikek\OneDrive - Hochschule Luzern\Semester 5\DT Programming\Coding Project\Beispiele_IfcOpenShell_Pandas SW4\25.011_GoBau.ifc")

kostenteilerset = {'WWZ-WV:100%', 'ZUG:100%', 'WWZ-EW:100%'}

def check_allowed(ifcsite_name:str, pset:str, property:str, allowed_values:set):
    results = [] #this will return the result of matching the property value with the allowed values.
    sites = [x for x in model.by_type('IfcSite') if x.Name == ifcsite_name] 

    #Check if Site Exists:
    if not sites:
        print(f"Error: No IFC site with the name '{ifcsite_name}' found.")
        return None

    site = sites[0]  # Get the first matching site
    
    inside = ifcopenshell.util.element.get_decomposition(site) #This returns to me all the elements under the site. 
    elements = [e for e in inside if e.is_a("IfcElement")] #Returns IFCElements as a List.

    #Check if Property Set (pset) and property Exists for each element:
    for i in elements:

        #Check if the Pset exists for the element:
        try:
            pset_exists = ifcopenshell.util.element.get_psets(i)[pset] # For each element, it either returns the Pset or raises a KeyError if the Pset doesn't exist.

        except KeyError:
            results.append({"GUID": i.GlobalId, "Name": i.Name, property: "Pset does not exist", "Check": "Pset does not exist"})
            continue  # Skip to the next element if the Pset doesn't exist

        #Check if the property exists in the Pset and if its value is in the allowed values:
        try:
            pset_properties = pset_exists[property]
            if pset_properties in allowed_values:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: pset_properties, "Check": "PASS"})
            
            else:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: pset_properties, "Check": "FAIL"})

        #Do this when the Pset exists, but the property does not exist in the Pset:
        except KeyError:
            results.append({"GUID": i.GlobalId, "Name": i.Name, property: "Property does not exist", "Check": "Property does not exist"})

    df_check_allowed = pd.DataFrame(results)
    return df_check_allowed



df = check_allowed("03 Neu", "GoBau_Ausschreibung", "Kostenteiler", kostenteilerset)
print(df)

df.to_csv("check_result.csv", index=False)