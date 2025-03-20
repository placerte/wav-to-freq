from plot_handler import Plotter
from file_handler import WavSampleFile
from tkinter import messagebox


def main():
    # Example usage:

    wav_file: WavSampleFile = WavSampleFile()

    wav_file.get_first_wav_filepath()

    if wav_file.filepath != "":
        pltr = Plotter(wav_file)
        pltr.show()
    else:
        messagebox.showerror("No wav file", "Could not find a wav file in the current directory.")

if __name__ == "__main__":
    main()
