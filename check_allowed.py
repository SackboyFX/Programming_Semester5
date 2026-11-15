import ifcopenshell
import pandas as pd
import ifcopenshell.util
import ifcopenshell.util.element
import operator

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



def check_type(ifcsite_name:str, pset:str, property:str, data_type:type):
    results = [] #this will return the result of checking the property value against the expected data type.
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
            results.append({"GUID": i.GlobalId, "Name": i.Name, property: "Pset does not exist", "Data Type": "N/A", "Check": "Pset does not exist"})
            continue  # Skip to the next element if the Pset doesn't exist

        #Check if the property exists in the Pset and if its value is of the correct data type:
        try:
            pset_properties = pset_exists[property]
            if isinstance(pset_properties, data_type):
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: pset_properties, "Data Type": data_type.__name__, "Check": "PASS"})
            
            else:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: pset_properties, "Data Type": data_type.__name__, "Check": "FAIL"})

        #Do this when the Pset exists, but the property does not exist in the Pset:
        except KeyError:
            results.append({"GUID": i.GlobalId, "Name": i.Name, property: "Property does not exist", "Data Type": "N/A", "Check": "Property does not exist"})

    df_check_type = pd.DataFrame(results)
    return df_check_type


def check_range(ifcsite_name:str, pset:str, property:str, conditional:str, compare_value:float):
    results = [] #this will return the result of comparing the property value with the compare value.
    sites = [x for x in model.by_type('IfcSite') if x.Name == ifcsite_name]

    #The idea is that we can use the operator module to map the string representation of the conditional to the actual comparison operation. This way, we can dynamically apply the correct comparison based on the user's input.
    operations = {
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "==": operator.eq,
        "!=": operator.ne
    }

    #Check if the conditional is valid (the keys of the operations dictionary are the allowed conditionals):
    if conditional not in operations:
        print(f"Error: Invalid conditional '{conditional}'. Allowed conditionals are: {list(operations)}")
        return None

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

        #Check if the property exists in the Pset and if its value passes the ruleset:
        try:
            pset_properties = pset_exists[property]

            #Check if the value is a number. Text or None would crash the comparison (TypeError) or give wrong results ("10" > "9" is False).
            #bool is excluded on purpose: in Python True/False count as 1/0, so True > 0 would pass.
            if not isinstance(pset_properties, (int, float)) or isinstance(pset_properties, bool):
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: pset_properties, "Check": "Not a number"})
                continue  # Skip to the next element, a comparison makes no sense here

            if operations[conditional](pset_properties, compare_value):
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: pset_properties, "Check": "PASS"})
            
            else:
                results.append({"GUID": i.GlobalId, "Name": i.Name, property: pset_properties,  "Check": "FAIL"})

        #Do this when the Pset exists, but the property does not exist in the Pset:
        except KeyError:
            results.append({"GUID": i.GlobalId, "Name": i.Name, property: "Property does not exist", "Check": "Property does not exist"})

    df_check_range = pd.DataFrame(results)
    return df_check_range




# df = check_allowed("03 Neu", "GoBau_Ausschreibung", "Kostenteiler", kostenteilerset)
# print(df)

# df = check_type("03 Neu", "GoBau_Ausschreibung", "Kostenteiler", int)
# print(df)

df = check_range("03 Neu", "GoBau_Menge", "Volumen (m3)", "==", 0.0)
print(df)

df.to_csv("check_range.csv", index=False)