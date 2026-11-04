from nicegui import ui, events
import ifcopenshell
from IfcModel import ifcmodel

ui.button("Test")

model = None

#Accept Upload Function
async def load_ifc(document):
    data = await document.file.read()                         # the file's bytes
    global model
    model = ifcopenshell.file.from_string(data.decode())  # decoding the bytes to a string and opening it directly from memory, setting it as the variable model
    print("A file arrived:", document.file.name)
    print(model.schema)

#Reject Upload Function
async def reject_file(document):
    ui.notify(f'File rejected - Only .IFC files allowed')

#Upload UI
ui.upload(on_upload=load_ifc,
          on_rejected=reject_file
          ).props('accept=.ifc')

ui.run()

