from plot_handler import Plotter
from file_handler import WavSampleFile

def main():
    # Example usage:

    wav_file: WavSampleFile = WavSampleFile()

    wav_file.get_first_wav_filepath()

    pltr = Plotter(wav_file)
    pltr.generate_plots()
    

if __name__ == "__main__":
    main()
