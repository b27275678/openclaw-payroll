import pandas as pd

def process_file(file):
    df = pd.read_excel(file, header=None)

    # Drop completely empty rows
    df = df.dropna(how='all')

    # Convert everything to string for easier searching
    df = df.astype(str)

    # Keep only rows that contain "In" or "Out"
    df = df[df.apply(lambda row: row.str.contains("In|Out", case=False).any(), axis=1)]

    # Extract columns manually (based on your file layout)
    df = df.reset_index(drop=True)

    # Guess positions (these match your screenshot)
    df["Employee"] = df[0]
    df["Action"] = df[1]
    df["Date"] = df[3]
    df["Time"] = df[4]

    # Combine date + time
    df["datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"], errors="coerce")

    # Sort
    df = df.sort_values(by=["Employee", "datetime"])

    # Calculate hours between punches
    df["hours"] = df.groupby("Employee")["datetime"].diff().dt.total_seconds() / 3600

    # Only count OUT rows
    df = df[df["Action"].str.lower() == "out"]

    # Drop bad rows
    df = df.dropna(subset=["hours"])

    # Final result
    result = df.groupby("Employee")["hours"].sum().reset_index()

    return result
