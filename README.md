# Wav to freq

An app that takes in a formatted wav file of an impact and returns its natural frequencies.

## How to use

1. Provide a small .wav sample of an impact (should be less than a coupl of seconds for performance)
2. Change the hardcoded filepath in the code so it loads the correct one (feature to be upgraded)
3. On the matplotlig graph, select points of interest that will be saved.

## TODOs

- [x] Basic fft of the wav file
- [x] Selection of points of interest on the GUI
- [x] Save as image and scatter points for post processing.
- [x] Solve the curve fitting to extract the natural frequency and the damping ratio (done seperatly for now)
- [ ] upgrade file handling at load and save moments
- [ ] Integrate file info, and solved parameters to the GUI
- [ ] Integrate live curve fitting and solving.
- [ ] Export solved parameters and file info.
- [ ] Make the code a protable executable
- [ ] Clean LSP warnings
- [ ] Remove the abundance of np.pi. It may affect numerical precision.
