from nicegui import ui, app
import ifcopenshell
import ifcopenshell.util
import ifcopenshell.util.element
from checker import Checker, rulecheck, savecheck, summarize, writeback
import pandas as pd
import io
import datetime


model = None            # the uploaded IFC model
ifc_name = None         # its file name, for the download name of the checked IFC
ruleset = None          # the uploaded rules Excel (sheet "Rules")
checker = None          # the Checker of the last check, needed for the write-back
results = None          # the results of the last check {sheet name: DataFrame}
sitelocation = "03 Neu"

######################################################### All Functions come here ###############################################################

#IFC Upload: Accept Upload Function
async def load_ifc(document):
    global model, ifc_name
    data = await document.file.read()                       # the file's bytes
    model = ifcopenshell.file.from_string(data.decode())    # IFC is text: decode the bytes and open the model directly from memory
    ifc_name = document.file.name
    print("A file arrived:", ifc_name)

#IFC Upload: Reject Upload Function
async def reject_ifc(document):
    ui.notify('File rejected - Only .IFC files allowed')

#Excel Upload: Accept Upload Function
async def load_excel_ruleset(excel):
    global ruleset
    data = await excel.file.read()                                  # the file's bytes
    ruleset = pd.read_excel(io.BytesIO(data), sheet_name="Rules")   # xlsx is binary: no decode, BytesIO makes the bytes look like a file
    print("A file arrived:", excel.file.name)

#Excel Upload: Reject Upload Function
async def reject_excel_ruleset(excel):
    ui.notify('File rejected - Only .xlsx files allowed')

#Check Ruleset Button: run all rules, then show the summary, the table dropdown and the download buttons
def runcheck():
    global checker, results

    if model is None or ruleset is None:
        ui.notify("Upload an IFC and a ruleset first")
        return

    checker = Checker(model, sitelocation)
    results = rulecheck(checker, ruleset)

    if not results:
        ui.notify("No rule could be checked - look at the terminal for errors")
        return

    #Summary: one row per rule with the counts
    summary_area.clear()
    with summary_area:
        ui.markdown("## Summary")
        ui.table.from_pandas(summarize(results))

    #Dropdown to look at the full table of one rule
    dropdown_area.clear()
    with dropdown_area:
        with ui.dropdown_button("Select Ruleset", auto_close=True):
            for tablename in results:
                # tablename=tablename freezes the value for each item (otherwise every item shows the last table)
                ui.item(tablename, on_click=lambda tablename=tablename: generatetable(results[tablename]))

    #Download buttons
    download_area.clear()
    with download_area:
        with ui.row():
            ui.button("Download Report (Excel)", on_click=download_report)
            ui.button("Download checked IFC", on_click=download_ifc)

    table_area.clear()  # remove the table of an earlier check

#Show the full result table of one rule in table_area
def generatetable(dftable):
    table_area.clear()          # remove the old table
    with table_area:            # "everything created in here goes into the box"
        ui.table.from_pandas(dftable).classes("max-h-100")

#Download Report button: write the Excel into memory and hand the bytes to the download
def download_report():
    buffer = io.BytesIO()                 # an empty "file" that lives in memory
    savecheck(results, buffer)            # ExcelWriter writes into it instead of onto disk
    ui.download.content(buffer.getvalue(), f"Rule Check {datetime.date.today()}.xlsx")

#Download checked IFC button: write PsetCheck into the model, then download the model as a new IFC
def download_ifc():
    writeback(checker, results)                         # adds/replaces PsetCheck on every checked element
    data = checker.model.to_string().encode()           # model → text → bytes (the upload, in reverse)
    name = ifc_name.removesuffix(".ifc") + "_checked.ifc"
    ui.download.content(data, name)



######################################################### All UI, NICEGUI comes here ###############################################################

#Upload IFC UI
ui.markdown("""# Upload IFC""")
ui.upload(on_upload=load_ifc,
          on_rejected=reject_ifc,
          auto_upload=True,      # upload right after choosing the file, no extra click
          ).props('accept=.ifc')

#Upload Excel Ruleset UI
ui.markdown("""# Upload Ruleset""")
ui.upload(on_upload=load_excel_ruleset,
          on_rejected=reject_excel_ruleset,
          auto_upload=True,
          ).props('accept=.xlsx')

#Check Ruleset button UI
ui.button("Check Ruleset", on_click=runcheck)

#Empty boxes, filled by runcheck() after a check, in this order below the button
summary_area = ui.column()      # summary table
download_area = ui.column()     # download buttons
dropdown_area = ui.column()     # dropdown to pick one rule
table_area = ui.column()        # full table of the picked rule




####################################################  Setup #########################################################################################

app.native.settings['ALLOW_DOWNLOADS'] = True
ui.run(native=True)
