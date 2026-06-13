## Project Name: PyMLRS (Self Project)
**Link/Repo:** [PyMLRS GitHub Repo](https://github.com/PyPCR/PyMLRS) / [PyPI Package](https://pypi.org/project/PyMLRS/)

### 1. The Problem
Clinical diagnosis of the Meningoencephalitis Panel (MEP) required time-consuming and error-prone manual interpretation. The Rotor-Gene machines export raw fluorescence data as complex XML-based `.rex` files. Clinicians had to manually extract, plot, and analyze High-Resolution Melt (HRM) and Amplification (CT) curves to identify pathogen severity, a massive bottleneck in critical care.

### 2. The Architecture & Approach
I built a 3-stage automated pipeline encapsulated in a Python library:
*   **Stage 1 - Raw Data Extraction (`Rextractor`):** Built a custom XML parser to extract raw Amplification and HRM channel readings, cycle times, and sample metadata directly from the proprietary `.rex` files without any manual preprocessing.
*   **Stage 2 - Feature Engineering & Signal Processing:** Cleaned noisy fluorescence data using Savitzky-Golay filters. Converted HRM curves to melt curves (calculating the negative derivative `-dF/dT`) and used peak-finding algorithms to extract critical features like Peak Temperatures (Tm), Prominence, Width, and Area Under the Curve (AUC) via Simpson's rule.
*   **Stage 3 - Diagnosis & Automated Reporting:** Passed extracted features into predefined threshold logic and a trained Scikit-Learn Machine Learning model to classify pathogen presence. The pipeline ultimately orchestrates FPDF, Matplotlib, and Plotly to generate comprehensive, automated PDF diagnostic reports.

### 3. Tech Stack
*   **Language:** Python 3
*   **Data Processing & Signal Analysis:** Pandas, NumPy, SciPy (Savitzky-Golay filters, peak detection, Simpson integration)
*   **Machine Learning:** Scikit-Learn (Linear Regression for take-off points, predictive model for classification)
*   **Visualization & Reporting:** Matplotlib, Plotly (Interactive charts), FPDF, Pillow
*   **Data Extraction:** XML ElementTree

### 4. The Hardest Technical Hurdle
**Hurdle:** Automating the detection of the Amplification curve's "Take-off Point" (CT) and accurately identifying Melt Curve peaks from extremely noisy raw fluorescence data. Distinguishing a true pathogen peak from machine noise was critical to avoid false positives/negatives.

**Solution:** I solved the noise issue by applying a `scipy.signal.savgol_filter` which smoothed the data while preserving curve shapes. To find the exact CT take-off point algorithmically, I fit a `LinearRegression` model over the initial baseline points and identified the exact index where the actual curve exponentially diverged from the regression line. For the Melt Curve, I calculated `-dF/dT` and utilized `scipy.signal.find_peaks` with custom prominence thresholds to isolate genuine pathogen signatures.

### 5. The Outcome
Published PyMLRS to PyPI as a production-stable library (v0.0.4). The library completely automates the diagnosis workflow, turning a manual, subjective interpretation of `.rex` files into a deterministic, programmatic process that generates a clear PDF report in seconds. This significantly minimizes human error and reduces manual workload for clinical pathogen interpretation.
