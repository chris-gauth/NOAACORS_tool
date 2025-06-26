import tkinter as tk
import os
import requests
import georinex as gr
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import sys
from PIL import Image, ImageTk
import webbrowser




#Global
target_file = None
user_enter_year = None
user_enter_month = None
user_enter_day = None
user_enter_startHr = None
user_enter_endHr = None
file_path = None
start_dtg = 0
end_dtg = 0
status_label = None
header_image = None

def get_app_folder():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS

    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_download_path(filename):
    base_folder = get_app_folder()
    download_folder = os.path.join(base_folder, "downloads")
    os.makedirs(download_folder, exist_ok=True)
    return os.path.join(download_folder, filename)

def open_web_link():
    webbrowser.open_new("https://www.arcgis.com/apps/mapviewer/index.html?webmap=261ff9458fd740d6a01b89558b8be1c5")

def analyze_snr(file_path, start_dtg, end_dtg):
    obs = gr.load(file_path)

    # Slice to the time window
    obs_window = obs.sel(time=slice(start_dtg, end_dtg))

    print("Obs types:", list(obs.data_vars))

    gps_sats = obs_window.sv[obs_window.sv.str.startswith('G')]

    # Select SNR data for L1, L2, L5 on GPS sats within time window
    snr_L1 = obs_window['S1'].sel(sv=gps_sats)
    snr_L2 = obs_window['S2'].sel(sv=gps_sats)
    snr_L5 = obs_window['S5'].sel(sv=gps_sats)

    # Convert to DataFrame
    df_L1 = snr_L1.to_dataframe().unstack(level='sv')
    df_L2 = snr_L2.to_dataframe().unstack(level='sv')
    df_L5 = snr_L5.to_dataframe().unstack(level='sv')

    # Plot in subplots
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    df_L1.plot(ax=axes[0], legend=False, title='SNR over time (L1)')
    axes[0].set_ylabel('SNR (dB-Hz)')

    df_L2.plot(ax=axes[1], legend=False, title='SNR over time (L2)')
    axes[1].set_ylabel('SNR (dB-Hz)')

    df_L5.plot(ax=axes[2], legend=True, title='SNR over time (L5)')
    axes[2].set_ylabel('SNR (dB-Hz)')
    axes[2].set_xlabel('Time (UTC)')

    plt.tight_layout()
    plt.show()

    os.remove(file_path)


def get_input():
    global start_dtg, end_dtg, file_path, status_label

    site_code = target_file.get()
    year = user_enter_year.get()
    month = user_enter_month.get()
    day = user_enter_day.get()
    start_hr = user_enter_startHr.get()
    end_hr = user_enter_endHr.get()

    status_label.config(text="Downloading file...")
    root.update_idletasks()

    #print("User input:")
    #print(f"Site: {site_code}, Year: {year}, Month: {month}, Day: {day}")
    #print(f"Start Hour: {start_hr}, End Hour: {end_hr}")

    # Download the file and get the path
    file_path = build_and_download_rinex(year, month, day, site_code)

    if file_path is None:
        status_label.config(text="Download failed. Check inputs and try again.", fg="red")
        #print("File download failed. Cannot proceed with analysis.")
        return

    try:
        # Build datetime objects for time slice
        y, m, d = int(year), int(month), int(day)
        sh, eh = int(start_hr), int(end_hr)

        start_dtg = datetime(y, m, d, sh)
        end_dtg = datetime(y, m, d, eh)

        status_label.config(text="Analyzing data...This may take a minute or two.")
        root.update_idletasks()

        # Run analysis on downloaded file with time window
        analyze_snr(file_path, start_dtg, end_dtg)

        status_label.config(text="Analysis complete.", fg="green")

    except Exception as e:
        status_label.config(text=f"Error: {e}", fg="red")
        print("Error parsing input times or analyzing data:", e)


def build_UI():
    global target_file, user_enter_year, user_enter_month, user_enter_day
    global user_enter_startHr, user_enter_endHr, status_label, header_image

    try:
        img_path = os.path.join(get_app_folder(), "header_image.PNG")
        image = Image.open(img_path)
        image = image.resize((800, 100), Image.Resampling.LANCZOS)
        header_image = ImageTk.PhotoImage(image)

        header_label = tk.Label(root, image=header_image)
        header_label.grid(row=0, column=0, columnspan=4, pady=10)

    except Exception as e:
        print(f"Could not load header image: {e}")


    # Correct: Label + Entry for CORS site
    tk.Label(root, text="Enter CORS site").grid(row=3, column=0)
    target_file = tk.Entry(root)
    target_file.grid(row=3, column=1)

    tk.Label(root, text="Enter Year").grid(row=4, column=0)
    user_enter_year = tk.Entry(root)
    user_enter_year.grid(row=4, column=1)

    tk.Label(root, text="Enter Month").grid(row=5, column=0)
    user_enter_month = tk.Entry(root)
    user_enter_month.grid(row=5, column=1)

    tk.Label(root, text="Enter Day").grid(row=6, column=0)
    user_enter_day = tk.Entry(root)
    user_enter_day.grid(row=6, column=1)

    tk.Label(root, text="Enter Start Hour").grid(row=7, column=0)
    user_enter_startHr = tk.Entry(root)
    user_enter_startHr.grid(row=7, column=1)

    tk.Label(root, text="Enter End Hour").grid(row=8, column=0)
    user_enter_endHr = tk.Entry(root)
    user_enter_endHr.grid(row=8, column=1)

    tk.Button(root, text="Submit", command=get_input).grid(row=14, column=0, columnspan=2, pady=10)
    status_label = tk.Label(root, text="", fg="red")
    status_label.grid(row=12, column=0, columnspan=2)

    tk.Button(root, text="Map of NOAA CORS Network", fg="blue", cursor="hand2", command=open_web_link).grid(row=20, column=0)


def build_and_download_rinex(year, month, day, site_code, destination_folder=None):
    global file_path
    try:
        dt = datetime(int(year), int(month), int(day))
        doy = dt.timetuple().tm_yday
        yy = dt.strftime("%y")
        yyyy = dt.strftime("%Y")
        site = site_code.lower()

        destination_folder = os.path.join(os.getcwd(), "downloads")


        filename = f"{site}{doy:03d}0.25o.gz"
        url = f"https://geodesy.noaa.gov/corsdata/rinex/{yyyy}/{doy:03d}/{site}/{filename}"

        destination_path = get_download_path(filename)
        file_path = destination_path

        #print(f"Downloading from: {url}")
        #print(f"Saving to: {destination_path}")

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(destination_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            #print("Download complete.")
            return destination_path
        else:
            #print(f"Download failed with status code {response.status_code}")
            return None

    except Exception as e:
        #print("Error during download:", e)
        return None

def time_slice(year, month, day, start_hour, end_hour, obs):
    global start_dtg, end_dtg
    try:
        # Convert all to integers
        y = int(year)
        m = int(month)
        d = int(day)
        sh = int(start_hour)
        eh = int(end_hour)

        # Build datetime objects in UTC
        start_dtg = datetime(y, m, d, sh)
        end_dtg = datetime(y, m, d, eh)

        # Slice the dataset by time
        time_window = obs.sel(time=slice(start_dtg, end_dtg))
        return time_window

    except Exception as e:
        #print("Error creating time slice:", e)
        return None


if __name__ == '__main__':
    root = tk.Tk()
    root.title("CORS Site Analysis Tool")
    root.geometry("800x600")
    build_UI()
    root.mainloop()
