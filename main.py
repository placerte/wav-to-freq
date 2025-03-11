from plot_handler import Plotter
from file_handler import get_first_wav_filepath

def main():
    # Example usage:

    file_base_name, wav_filepath = get_first_wav_filepath()

    pltr = Plotter(file_base_name=file_base_name, wav_filepath=wav_filepath)

    pltr.generate_plots()
    

if __name__ == "__main__":
    main()
