import os
import pandas as pd
from pathlib import Path

BASE_DIR = Path("./")
ARCHIVE_DIR = BASE_DIR / "archive"
CONSOLIDATED_DIR = ARCHIVE_DIR / "consolidated"

CONSOLIDATED_DIR.mkdir(exist_ok=True)

def main():
    dirs = os.listdir(ARCHIVE_DIR.absolute())
    for dir in dirs:
        filepath = Path(ARCHIVE_DIR / dir)
        if filepath.is_file():
            filename = filepath.stem
            output_filename = f"{filename}_Consolidated.xlsx"
            if output_filename in list(os.listdir(CONSOLIDATED_DIR)):continue
            print(f"Processing {filename}")
            sheets = list(pd.read_excel(filepath, sheet_name=None))
            print("Total Pages:", len(sheets))
            df_dict = {}
            for sheet in sheets:
                df = pd.read_excel(filepath, sheet_name=sheet)
                for column in df.columns:
                    if column=="Total Billing Amount":continue
                    if column in df_dict:
                        df_dict[column] += list(df[column])
                    else:
                        df_dict[column] = list(df[column])
            df = pd.DataFrame(df_dict)
            df.drop_duplicates(subset="Customer Mobile", inplace=True, keep=False)
            print("Total Unique Customer Mobile: ", len(df["Customer Mobile"]))
            if not df.empty:
                filepath = CONSOLIDATED_DIR / output_filename
                df.to_excel(filepath, sheet_name="All", index=False)
        print("################## DONE ##################")
    print("############################################ COMPLETED ############################################")

            
    
if __name__ == "__main__":
    main()