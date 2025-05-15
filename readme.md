# Notebook Automation Script

## Overview

This Python script (bootcamp.py) automates the process of cloning or updating a Git repository, setting up a Conda environment, converting Jupyter notebooks to Python scripts, refactoring environment variables, running the converted scripts, and generating a test report. It also includes cleanup operations to remove temporary files and Conda environments after execution.

## Prerequisites

- **Python >= 3.10**
- **Conda**
- **OpenAI API Key**: If you want to use the OpenAI API for refactoring, you need to set your own `OPENAI_API_KEY` in the `.env` file.

## How to use?

1. **Clone the Automation Script Repository**

   ```bash
   git clone https://github.com/Shawnzheng011019/notbook_automation
   cd bootcamp_automation
   ```

2. **Clone the Target Project Repository**

   ```bash
   git clone https://github.com/Shawnzheng011019/bootcamp
   ```

3. **Execute the Automation Script**

   ```bash
   python bootcamp.py
   ```

*This script automatically converts all `.ipynb` files in the configured directory, runs automated tests, and generates test reports and execution logs.*

## Execution Steps

### 1. Initialization

- **Logging Setup**: The script creates a log directory (`logs`) and a log file named `bootcamp_YYYYMMDD.log` to record all the execution details.
- **Load Environment Variables**: It loads the environment variables from the `.env` file.

### 2. Repository Management

- **Clone or Update**: If the project directory does not exist, the script clones the repository using the `git clone` command. Otherwise, it updates the existing repository using `git pull`.

### 3. Conda Environment Setup

- **Create and Activate**: For each notebook, the script creates a Conda environment with Python 3.9 if it does not already exist. The environment name is derived from the notebook's stem.
- **Install Dependencies**: It installs the `openai` package in the Conda environment using `pip`.

### 4. Notebook Conversion

- **Convert to Python**: The script converts each Jupyter notebook to a Python script using the `ipynb_converter.py` script. If the converted Python file does not exist, it runs the converter script.

### 5. Environment Variable Refactoring

- **OpenAI API**: If the `OPENAI_API_KEY` is set in the `.env` file, the script uses the `refactor_env_vars.py` script to refactor the environment variables in the converted Python script using the OpenAI API.
- **Fallback Method**: If the OpenAI API key is not set or the refactoring using the API fails, the script uses a fallback method to replace the hardcoded API key references with a reference to the `.env` file.

### 6. Script Execution

- **Run Shell Script**: The script runs the converted shell script (if it exists) in the Conda environment using `conda run`.
- **Run Python Script**: It then runs the converted Python script in the Conda environment, loading the API key from the `.env` file.

### 7. Test Report Generation

- **Success and Failure Tracking**: The script keeps track of the successful and failed files during execution.
- **Markdown Report**: It generates a Markdown test report named `test_report_YYYYMMDD.md` in the `reports` directory, including details such as execution time, success rate, and a list of successful and failed files.

### 8. Cleanup

- **Remove Conda Environments**: The script removes all the created Conda environments using `conda env remove`.
- **Remove Temporary Files**: It deletes all the converted Python and shell scripts, as well as any backup files created during the refactoring process.
- **Remove Images Folder**: If the `images_folder` exists, the script removes it using `shutil.rmtree`.

## Usage

To run the script, simply execute it from the command line:

```bash
python bootcamp.py
```

## Test Report Example

The script generates a Markdown report (`test_report_YYYYMMDD.md`) in the `reports/` directory. Below is an example of its structure and content:

```markdown
# Test Execution Report
- Execution Date: 2025-05-15 14:30:45
- Execution Time: 124.56 seconds
- Total Number of Files: 5
- Number of Successful Files: 3
- Number of Failed Files: 2
- Success Rate: 60.00%

## Execution Result Statistics
| Category                | Quantity | Proportion |
|-------------------------|----------|------------|
| Successful Files        | 3        | 60.00%     |
| Host Dependency Failed Files | 1      | 20.00%     |
| Python Failed Files     | 1        | 20.00%     |
| Total                   | 5        | 100%       |

## List of Successful Files
| File                                  |
|---------------------------------------|
| bootcamp/tutorials/quickstart/rag.ipynb |
| bootcamp/tutorials/quickstart/image_search.ipynb |
| bootcamp/tutorials/quickstart/hybrid_search.ipynb |

## List of Failed Files
| File                                  | Error Type         | Error Message                                                                 |
|---------------------------------------|--------------------|-----------------------------------------------------------------------------|
| bootcamp/tutorials/quickstart/clustering.ipynb | Host Dependency    | CalledProcessError: Failed to execute command: conda run -n clustering_env bash clustering.sh (Permission denied) |
| bootcamp/tutorials/quickstart/nlp.ipynb        | Python Error       | RuntimeError: Python script execution failed with return code: 1 (ModuleNotFoundError: No module named 'transformers') |
```

## Error Handling

- **Command Execution**: If any shell command fails during execution, the script logs the error and raises an appropriate exception.
- **File Not Found**: If a required file (such as the converted Python file) is not found, the script logs the error and raises a `FileNotFoundError`.
- **Runtime Errors**: If a runtime error occurs during script execution, the script logs the error, adds the file to the list of failed files, and continues with the next file.

## Known Issues

1. **Incomplete Cleanup Functionality**:
   - The script does not fully delete downloaded data files or model files.
   - **Action Required**: Manually remove residual files in the `bootcamp/` directory after execution.
2. **PyArrow Environment Instability**:
   - `pyarrow` may fail to install or run correctly without proper system dependencies.
   - Prerequisite `CMake` is installed on your system before running the script.
     - For Ubuntu/Debian: `sudo apt-get install cmake`
     - For macOS: `brew install cmake`
     - For Windows: Install via [CMake official website](https://cmake.org/install/)
