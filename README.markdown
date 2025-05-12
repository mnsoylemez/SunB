# SunB - Solar Panel Tilt Angle Calculator

SunB is a Python application designed to calculate the maximum tilt angles required for solar panels to optimize energy production based on solar position vectors. It uses the `pvlib` library to compute solar positions and energy production for specified locations and generates detailed reports and visualizations.

## Features
- Calculate solar position vectors for any given location and year.
- Determine optimal panel tilt angles (East-West, North-South, and total tilt).
- Estimate energy production based on panel efficiency and area.
- Generate daily and monthly statistics for tilt angles and energy production.
- Export results to an Excel file with summaries, daily/monthly data, and explanatory notes.
- Visualize tilt angles and energy production with matplotlib plots embedded in a Tkinter GUI.

## Installation

### Prerequisites
- Python 3.8 or higher
- Git (for cloning the repository)

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/mnsoylemez/SunB.git
   cd SunB
   ```

2. **Create a Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. **Run the Application**:
   ```bash
   python SunB.py
   ```

2. **GUI Instructions**:
   - **Add Locations**: Enter the name, latitude, longitude, and timezone for each location. Use the "+ Konum Ekle" button to add more locations.
   - **Set Parameters**: Specify the start year and panel efficiency (as a percentage, e.g., 20 for 20%).
   - **Calculate and Export**: Click "Hesapla ve Eğim Açılarını Dışa Aktar" to compute tilt angles and energy production. Choose a file path to save the Excel output.
   - **View Results**: The GUI displays plots for the first location's tilt angles and energy production. Excel files and PNG plots are saved to the specified directory.

3. **Output**:
   - **Excel File**: Contains sheets for summary, daily data, monthly data, and column descriptions.
   - **Plots**: PNG files for each location showing East-West tilt, North-South tilt, and daily energy production.

## Requirements
See `requirements.txt` for the list of required Python packages. Key dependencies include:
- `tkinter` (usually included with Python)
- `pandas`
- `numpy`
- `pvlib`
- `matplotlib`
- `openpyxl`

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

Please ensure your code follows PEP 8 style guidelines and includes appropriate tests.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact
For questions or suggestions, please open an issue on the [GitHub repository](https://github.com/mnsoylemez/SunB) or contact the maintainer at [your-email@example.com].