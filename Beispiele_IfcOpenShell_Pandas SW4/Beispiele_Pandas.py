import pandas as pd

base_file_path_1 = r"C:\Users\MichalRontsinsky\OneDrive - beyondBIM\Dokumente\VS_Projects\HSLU_PROGR_Test_02_HS25\Raumliste_Demo.xlsx"

my_df = pd.read_excel(base_file_path_1, sheet_name="Sheet1")

#Beispiel zum Filtern der Spalten
my_df_short = my_df[["Geschosscode","SIA416", "Raumflaeche [m²]"]]

#Beispiel zum Filtern der Werte
my_df_hnf = my_df_short[my_df_short["SIA416"] == "HNF"]
#print(my_df_hnf)

summe_netto_flaeche = my_df_hnf["Raumflaeche [m²]"].sum()
#print(summe_netto_flaeche)


#Beispiel für loc

filter_loc_df = my_df.loc[ : , "SIA416"]
#print(filter_loc_df)


#Beispiel für iloc
filter_iloc_df = my_df.iloc[ 0:10, my_df.columns.get_loc("SIA416")]
print(filter_iloc_df)









