import ifcopenshell
import ifcopenshell.util.element

def get_IsExternal(ele):
    all_psets = ifcopenshell.util.element.get_psets(ele,psets_only=False)

    target_pset = all_psets.get("Pset_WallCommon","")
    target_prop = target_pset.get("IsExternal","")
    print(target_prop)


def get_ElementStorey(ele):
    all_containers = ifcopenshell.util.element.get_container(ele)
    print(all_containers.Name)


model_path = r"C:\Users\MichalRontsinsky\OneDrive - beyondBIM\PERSONAL\PROJEKTE\HSLU\Digital Construction Scripting HS24\HSLU_LiveCoding_01\HSLU_LiveCoding_01\ARC_Modell_NEST_230328.ifc"

ifc_model = ifcopenshell.open(model_path)
all_walls = ifc_model.by_type("IfcWallStandardCase")

wall_psets = ifcopenshell.util.element.get_psets(all_walls[0], psets_only=False)
#print(wall_psets)

for wall in all_walls:
    #get_IsExternal(wall)
    #get_ElementStorey(wall)

    #Abfrage der Basis Daten und Attribute
    current_info = wall.get_info()
    print(current_info)



