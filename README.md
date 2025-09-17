# Delirium Visualization
Paranal/UFRO collaboration project to visualize rail adjustment heatmap over time based on Delirium daily calibrations. 2025, second semester.

## Description

This project aims to visualize the heatmap of the rail adjustments over time based on daily correction files. 

## Objectives and Scope

- Develop a **descriptive analysis tool** from accumulated daily reports.  
- Combine individual corrections into a single dataset and **visualize deviations as a heatmap** over the tunnel layout.  
- Provide a **Jupyter notebook** as final deliverable, parameterized by:
  - Start/end time
  - Delay line number  
- Implement a function that parses multiple HTML daily reports, returning a structured `pandas.DataFrame` with correction values.  
- Display the heatmap on top of a provided image which represents the real tunnel.
- As a desirable, provide a **Streamlit** for user-friendly exploration.

## Collaboration Rules

This project is a joint effort between Paranal and UFRO, and collaboration requires consistency and discipline. To ensure smooth teamwork, please follow these rules:

1. **Read the README in every subdirectory**  
   Each folder (`data`, `src`, `notebooks`, `reports`, `deliverables`) has its own `README.md`.  
   All contributors must read and respect the guidelines defined there before adding or modifying content.

2. **Respect the core API**  
   The following functions must exist and their APIs **must not change**:  
   - `corrections_loader` → parses daily HTML reports and returns a structured `pandas.DataFrame`.  
   - `heatmap` → generates the heatmap visualization over the tunnel layout.  
   These functions are the foundation of the project. You may extend or override them in separate modules, but do not modify their interfaces.

3. **Collaboration workflow**  
   - Use the private GitHub repository for commits, issues, and reviews.  
   - Follow the repo structure and place files in the correct subdirectory.  
   - Document decisions and context in `reports/`.  
   - Place experimental work in `notebooks/`, and move only final results to `deliverables/`.


## Data and Confidentiality

- Input data: daily HTML reports from delay line calibrations (2022 winter data as first example).  
- Confidentiality:  
  - Data is not highly sensitive, but usage requires confidentiality agreements.
  - Data shall not be distributed in this repository.

## Tools and Platforms

- Python / Jupyter Notebook  
- Pandas for parsing and analysis  
- Streamlit (optional) for interactive visualization  
- GitHub for version control and collaboration  
- Suggestion: Use matplotlib + pillow to render heatmap over images

## Repo structure

* [data](./data): Sample HTML calibration files and datasets  
* [src](./src): Core functions (`heatmap`, `corrections_loader`, etc.)  
* [notebooks](./notebooks): Jupyter notebooks for iterative development  
* [reports](./reports): Meeting notes, PDFs, or intermediate results  
* [deliverables](./deliverables): Final version of the Jupyter notebook

## Install
Create and activate a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows PowerShell
```

From repo root execute:
```bash
pip install --upgrade pip
pip install -e .
```

This allows Jupyter and Python to import directly:
```python
from deliriumviz import heatmap, corrections_loader
```

## Licence
BSD 3-Clause License, see attached license file.

