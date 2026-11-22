from nicegui import ui, events
import ifcopenshell
import ifcopenshell.util
import ifcopenshell.util.element
from checker import Checker, rulecheck, savecheck
import pandas as pd
import io


model = None
ruleset = None
sitelocation = "03 Neu"

######################################################### All Functions come here ###############################################################

#IFC Upload: Accept Upload Function
async def load_ifc(document):
    data = await document.file.read()                         # the file's bytes
    global model
    model = ifcopenshell.file.from_string(data.decode())  # decoding the bytes to a string and opening it directly from memory, setting it as the variable model
    print("A file arrived:", document.file.name)

#IFC Upload: Reject Upload Function
async def reject_ifc(document):
    ui.notify(f'File rejected - Only .IFC files allowed')

#Excel Upload: Accept Upload Function
async def load_excel_ruleset(excel):
    data = await excel.file.read()                         # the file's bytes
    global ruleset
    ruleset = pd.read_excel(io.BytesIO(data), sheet_name="Rules")  # decoding the bytes to a string and opening it directly from memory, setting it as the variable model
    print("A file arrived:", excel.file.name)

#Excel Upload: Reject Upload Function
async def reject_excel_ruleset(excel):
    ui.notify(f'File rejected - Only .xlsx files allowed')

#Check Ruleset Button: Run the necessary rulecheck functions
def runcheck():
    model_check = Checker(model, sitelocation)
    dftable = rulecheck(model_check,ruleset)
    
    with ui.dropdown_button("Select Ruleset", auto_close=True):   
        for tablename, tabledf in dftable.items():
            ui.item(tablename, on_click=lambda tablename=tablename: generatetable(dftable[str(tablename)]))
            #It’s a default value, the same as def f(x=5):. That value gets fixed at the moment the lambda is created, so each item gets its own copy of the name.
            #Why it went wrong without it. Without =tablename, the lambda doesn’t store a value. It only stores the instruction “look up the variable tablename when clicked.” The loop reuses that one variable:

#Generating Summary Table for table_area
def generatetable(dftable):
    table_area.clear()          # remove the old table
    with table_area:            # "everything created in here goes into the box"
        ui.table.from_pandas(dftable).classes("max-h-100")



######################################################### All UI, NICEGUI comes here ###############################################################

#Upload IFC UI
ui.markdown("""# Upload IFC""")
ui.upload(on_upload=load_ifc,
          on_rejected=reject_ifc
          ).props('accept=.ifc')

#Upload Excel Ruleset UI
ui.markdown("""# Upload Ruleset""")
ui.upload(on_upload=load_excel_ruleset,
          on_rejected=reject_excel_ruleset
          ).props('accept=.xlsx')

#Check Ruleset button UI
ui.button("Check Ruleset", on_click=runcheck)

#Show Table area, appears beneath Ruleset Button.
table_area = ui.column()        # top level, below your button: an empty "box"

ui.run()

