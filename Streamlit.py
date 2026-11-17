from nicegui import ui, events
import ifcopenshell
import ifcopenshell.util
import ifcopenshell.util.element
from checker import Checker, rulecheck
import pandas as pd
import io

ui.button("Test")

model = None
ruleset = None
sitelocation = "03 Neu"

######################################################### Uploading Files ###############################################################

#Accept Upload Function
async def load_ifc(document):
    data = await document.file.read()                         # the file's bytes
    global model
    model = ifcopenshell.file.from_string(data.decode())  # decoding the bytes to a string and opening it directly from memory, setting it as the variable model
    print("A file arrived:", document.file.name)


#Return IFC Course count
def ifc_course_count():
    roads = model.by_type('IfcCourse')
    ui.label(f"Number of Courses: {len(roads)}")


#Return Data Type
def ifc_data_type():
    road = model.by_type('IfcCourse')
    datatype = ifcopenshell.util.element.get_psets(road[0])["GoBau_Menge"]["Volumen (m3)"]
    ui.label(f"Data Type: {type(datatype)}")


#Reject Upload Function
async def reject_ifc(document):
    ui.notify(f'File rejected - Only .IFC files allowed')

#Upload UI
ui.markdown("""# Upload IFC""")
ui.upload(on_upload=load_ifc,
          on_rejected=reject_ifc
          ).props('accept=.ifc')


################################# Excel upload


#Accept Upload Function
async def load_ruleset(excel):
    data = await excel.file.read()                         # the file's bytes
    global ruleset
    ruleset = pd.read_excel(io.BytesIO(data), sheet_name="Rules")  # decoding the bytes to a string and opening it directly from memory, setting it as the variable model
    print("A file arrived:", excel.file.name)

#Reject Upload Function
async def reject_ruleset(excel):
    ui.notify(f'File rejected - Only .xlsx files allowed')

#Ruleset upload UI
ui.markdown("""# Upload Ruleset""")
ui.upload(on_upload=load_ruleset,
          on_rejected=reject_ruleset
          ).props('accept=.xlsx')


def runcheck():
    model_check = Checker(model, sitelocation)
    dftable = rulecheck(model_check,ruleset)
    
    with ui.dropdown_button("Select Ruleset", auto_close=True):   
        for tablename, tabledf in dftable.items():
            ui.item(tablename, on_click=lambda tablename=tablename: generatetable(dftable[str(tablename)]))
            #It’s a default value, the same as def f(x=5):. That value gets fixed at the moment the lambda is created, so each item gets its own copy of the name.
            #Why it went wrong without it. Without =tablename, the lambda doesn’t store a value. It only stores the instruction “look up the variable tablename when clicked.” The loop reuses that one variable:

ui.button("Check Ruleset", on_click=runcheck)

table_area = ui.column()        # top level, below your button: an empty "box"

def generatetable(dftable):
    table_area.clear()          # remove the old table
    with table_area:            # "everything created in here goes into the box"
        ui.table.from_pandas(dftable).classes("max-h-100")

ui.run()