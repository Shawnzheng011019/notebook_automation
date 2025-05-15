#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import logging
import shutil

log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"bootcamp_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Configuration - Load from environment variables or default values
REPO_URL = os.getenv("REPO_URL", "https://github.com/Shawnzheng011019/bootcamp.git")
PROJECT_DIR = os.getenv("PROJECT_DIR", "bootcamp")
NOTEBOOK_DIR = Path(os.getenv("NOTEBOOK_DIR", "bootcamp/bootcamp/tutorials/quickstart"))
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE = SCRIPT_DIR / ".env"
IPYNB_CONVERTER = SCRIPT_DIR / "ipynb_converter.py"
REFACTOR_SCRIPT = SCRIPT_DIR / "refactor_env_vars.py"
REPORT_DIR = SCRIPT_DIR / "reports"
REPORT_FILE = REPORT_DIR / f"test_report_{datetime.now().strftime('%Y%m%d')}.md"

def run_command(command: list, **kwargs) -> None:
    """Execute a shell command and handle errors"""
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            **kwargs
        )
        logging.info(f"Command executed successfully: {' '.join(map(str, command))}")
        logging.info(result.stdout)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to execute command: {' '.join(map(str, e.cmd))}")
        logging.error(e.stdout)
        print(f"Failed to execute command: {' '.join(map(str, e.cmd))}")
        print(e.stdout)
        raise

def setup_conda_env(env_name: str) -> None:
    """Create and activate a conda environment"""
    logging.info(f"Creating and activating conda environment: {env_name}")
    print(f"Creating and activating conda environment: {env_name}")
    conda_info = subprocess.run(
        ["conda", "info", "--base"],
        check=True,
        stdout=subprocess.PIPE,
        text=True
    )
    conda_base = conda_info.stdout.strip()
    conda_init = Path(conda_base) / "etc/profile.d/conda.sh"

    if not conda_init.exists():
        logging.error("Unable to find conda initialization script. Please ensure conda is correctly installed.")
        print("Unable to find conda initialization script. Please ensure conda is correctly installed.")
        sys.exit(1)

    env_exists = subprocess.run(
        ["conda", "env", "list"],
        check=True,
        stdout=subprocess.PIPE,
        text=True
    )
    if env_name not in env_exists.stdout:
        logging.info(f"Creating conda environment: {env_name}")
        print(f"Creating conda environment: {env_name}")
        run_command(["conda", "create", "-n", env_name, "python=3.9", "-y"])

def configure_environment() -> None:
    """Load environment variables from .env file"""
    logging.info("Loading environment variables from .env file...")
    print("Loading environment variables from .env file...")
    load_dotenv(ENV_FILE)

def clone_or_update_repo() -> None:
    """Clone or update the Git repository"""
    if not Path(PROJECT_DIR).exists():
        logging.info("Cloning repository...")
        print("Cloning repository...")
        run_command(["git", "clone", REPO_URL])
    else:
        logging.info("Updating existing repository...")
        print("Updating existing repository...")
        run_command(["git", "pull", "origin", "master"], cwd=PROJECT_DIR)

def convert_notebook(notebook_path: Path) -> Path:
    """Convert a Jupyter Notebook to a Python script"""
    logging.info(f"Converting Notebook: {notebook_path}")
    print(f"Converting Notebook: {notebook_path}")
    base_name = notebook_path.stem
    script_dir = notebook_path.parent
    converted_py = script_dir / f"{base_name}.py"

    logging.info(f"Checking converted Python file: {converted_py}")
    print(f"Checking converted Python file: {converted_py}")
    if not converted_py.exists():
        logging.info(f"Error: Converted Python file not found. Running ipynb_converter.py...")
        print(f"Error: Converted Python file not found. Running ipynb_converter.py...")
        run_command(["python", IPYNB_CONVERTER, str(notebook_path)])

        if not converted_py.exists():
            logging.error("Error: Unable to generate Python file from Notebook.")
            print("Error: Unable to generate Python file from Notebook.")
            raise FileNotFoundError(f"Unable to generate {converted_py}")

    return converted_py

def refactor_environment_variables(converted_py: Path) -> None:
    """Refactor environment variable handling using OpenAI API"""
    logging.info("Refactoring environment variables using OpenAI API...")
    print("Refactoring environment variables using OpenAI API...")
    load_dotenv(ENV_FILE)
    openai_api_key = os.getenv("OPENAI_API_KEY", "EMPTY")

    if openai_api_key == "EMPTY":
        logging.warning("Warning: Using default OpenAI API key. Skipping OpenAI refactoring...")
        print("Warning: Using default OpenAI API key. Skipping OpenAI refactoring...")
        if converted_py.exists():
            os.replace(converted_py, f"{converted_py}.bak")
            with open(f"{converted_py}.bak", "r") as f:
                content = f.read()

            content = content.replace(
                'os.environ["OPENAI_API_KEY"] = ...',
                '# Removed by script - use .env instead'
            )
            if "from dotenv import load_dotenv" not in content:
                content = "from dotenv import load_dotenv\n" + content
                main_pos = content.find("if __name__ == \"__main__\":")
                if main_pos != -1:
                    indent = content[main_pos:].splitlines()[0][:main_pos - content.rfind('\n', 0, main_pos)]
                    content = content[:main_pos] + f"{indent}load_dotenv()\n" + content[main_pos:]

            with open(converted_py, "w") as f:
                f.write(content)
            logging.info("Updated environment variable handling using fallback method")
            print("Updated environment variable handling using fallback method")
        else:
            logging.error(f"Converted Python file not found: {converted_py}")
            print(f"Converted Python file not found: {converted_py}")
            raise FileNotFoundError(f"Converted Python file not found: {converted_py}")
    else:
        try:
            refactored_code = subprocess.check_output(
                ["python", str(REFACTOR_SCRIPT), str(converted_py)],
                text=True,
                stderr=subprocess.STDOUT
            )
            with open(converted_py, "w") as f:
                f.write(refactored_code)
            logging.info("Environment variables refactored using OpenAI API (cell-by-cell).")
            print("Environment variables refactored using OpenAI API (cell-by-cell).")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error during OpenAI refactoring: {e.output}")
            print(f"Error during OpenAI refactoring: {e.output}")
            print("Falling back to manual replacement...")
            if converted_py.exists():
                os.replace(converted_py, f"{converted_py}.bak")
                with open(f"{converted_py}.bak", "r") as f:
                    content = f.read()

                content = content.replace(
                    'os.environ["OPENAI_API_KEY"] = ...',
                    '# Removed by script - use .env instead'
                )
                if "from dotenv import load_dotenv" not in content:
                    content = "from dotenv import load_dotenv\n" + content
                    main_pos = content.find("if __name__ == \"__main__\":")
                    if main_pos != -1:
                        indent = content[main_pos:].splitlines()[0][:main_pos - content.rfind('\n', 0, main_pos)]
                        content = content[:main_pos] + f"{indent}load_dotenv()\n" + content[main_pos:]

                with open(converted_py, "w") as f:
                    f.write(content)
                logging.info("Updated environment variable handling using fallback method")
                print("Updated environment variable handling using fallback method")
            else:
                logging.error(f"Converted Python file not found: {converted_py}")
                raise FileNotFoundError(f"Converted Python file not found: {converted_py}")

def run_converted_scripts(converted_py: Path, env_name: str) -> None:
    """Run the converted shell and Python scripts"""
    base_name = converted_py.stem
    script_dir = converted_py.parent
    converted_sh = script_dir / f"{base_name}.sh"

    logging.info(f"Running converted shell script: {converted_sh}")
    print(f"Running converted shell script: {converted_sh}")
    if converted_sh.exists():
        try:
            run_command(["conda", "run", "-n", env_name, "bash", str(converted_sh)])
        except subprocess.CalledProcessError as e:
            logging.error(f"Shell script execution failed: {e.output}")
            print(f"Shell script execution failed: {e.output}")
            raise RuntimeError("Host dependency issue")

    logging.info("Running converted Python script...")
    print("Running converted Python script...")
    load_dotenv(ENV_FILE)
    logging.info(f"Loaded API key: {os.getenv('OPENAI_API_KEY')}")
    print(f"Loaded API key: {os.getenv('OPENAI_API_KEY')}")

    result = subprocess.run(
        ["conda", "run", "-n", env_name, "python", str(converted_py)],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    logging.info(result.stdout)
    print(result.stdout)

    if result.returncode != 0:
        logging.error(f"Python script execution failed with return code: {result.returncode}")
        print(f"Python script execution failed with return code: {result.returncode}")
        raise RuntimeError(f"Python script execution failed with return code: {result.returncode}")

def get_last_lines(log_content: str, num_lines: int = 5) -> list[str]:
    """Get the last few lines of a string"""
    if not log_content:
        return []
    lines = log_content.strip().split('\n')
    return lines[-num_lines:] if len(lines) > num_lines else lines

def generate_markdown_report(
    success_files: list[str],
    host_dependency_failed_files: list[tuple[str, str]],
    python_failed_files: list[tuple[str, str]],
    total_files: int,
    execution_time: float,
    logs_dict: dict[str, list[str]]
) -> None:
    """Generate a Markdown formatted test report"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    success_rate = len(success_files) / total_files * 100 if total_files > 0 else 0
    
    success_table_header = 'None' if not success_files else '| File |\n|------|'
    failed_table_header = 'None' if not (host_dependency_failed_files + python_failed_files) else '| File | Error Type | Error Message |\n|------|------------|-------------|'
    
    markdown_content = f"""# Test Execution Report
- Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Execution Time: {execution_time:.2f} seconds
- Total Number of Files: {total_files}
- Number of Successful Files: {len(success_files)}
- Number of Failed Files: {len(host_dependency_failed_files) + len(python_failed_files)}
- Success Rate: {success_rate:.2f}%

## Execution Result Statistics
| Category       | Quantity   | Proportion        |
|------------|--------|-------------|
| Successful Files   | {len(success_files)}  | {success_rate:.2f}% |
| Host Dependency Failed Files   | {len(host_dependency_failed_files)}  | {len(host_dependency_failed_files) / total_files * 100 if total_files > 0 else 0:.2f}% |
| Python Failed Files   | {len(python_failed_files)}  | {len(python_failed_files) / total_files * 100 if total_files > 0 else 0:.2f}% |
| Total       | {total_files}  | 100%        |

## List of Successful Files
{success_table_header}
"""
    for file in success_files:
        markdown_content += f"| {file} |\n"
    
    markdown_content += f"""
## List of Failed Files
{failed_table_header}
"""
    # Merge two types of failed files and add error type
    all_failed_files = [
        (file, "Host Dependency", error) for file, error in host_dependency_failed_files
    ] + [
        (file, "Python Error", error) for file, error in python_failed_files
    ]
    
    for file, error_type, error in all_failed_files:
        escaped_error = str(error).replace("|", "\\|")[:200]
        markdown_content += f"| {file} | {error_type} | {escaped_error} |\n"
    
    with open(REPORT_FILE, "w") as f:
        f.write(markdown_content)
    
    print(f"\n✓ Test report generated: {REPORT_FILE}")

def cleanup(env_names: list[str], notebook_dir: Path) -> None:
    """Clean up created conda environments and temporary files"""
    for env_name in env_names:
        try:
            logging.info(f"Removing conda environment: {env_name}")
            print(f"Removing conda environment: {env_name}")
            subprocess.run(
                ["conda", "env", "remove", "-n", env_name, "-y"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to remove conda environment {env_name}: {e.stdout}")
            print(f"Failed to remove conda environment {env_name}: {e.stdout}")
        except Exception as e:
            logging.error(f"Unknown error removing conda environment {env_name}: {e}")
            print(f"Unknown error removing conda environment {env_name}: {e}")

    for ext in ['.py', '.sh', '.bak']:
        for file in notebook_dir.glob(f"*{ext}"):
            try:
                logging.info(f"Removing file: {file}")
                print(f"Removing file: {file}")
                file.unlink()
            except Exception as e:
                logging.error(f"Failed to remove file {file}: {e}")
                print(f"Failed to remove file {file}: {e}")

if __name__ == "__main__":
    import time
    start_time = time.time()
    env_names = []

    try:
        #clone_or_update_repo()
        configure_environment()

        success_files = []
        host_dependency_failed_files = []
        python_failed_files = []
        total_files = 0
        logs_dict = {}

        all_notebooks = list(NOTEBOOK_DIR.glob("*.ipynb"))
        total_files = len(all_notebooks)

        if not all_notebooks:
            logging.info("No .ipynb files found")
            print("No .ipynb files found")
            sys.exit(0)

        for notebook_path in all_notebooks:
            file_logs = []
            try:
                env_name = notebook_path.stem + "_env"
                env_names.append(env_name)
                logging.info(f"\nProcessing {notebook_path}, using environment: {env_name}")
                print(f"\nProcessing {notebook_path}, using environment: {env_name}")

                setup_conda_env(env_name)
                logging.info("Installing openai package...")
                print("Installing openai package...")
                run_command(["conda", "run", "-n", env_name, "pip", "install", "openai"])

                converted_py = convert_notebook(notebook_path)
                file_logs.append(f"Converted to {converted_py}")
                logging.info(f"Converted to {converted_py}")

                refactor_environment_variables(converted_py)
                file_logs.append("Environment variables refactored")
                logging.info("Environment variables refactored")

                run_converted_scripts(converted_py, env_name)
                file_logs.append("Script execution successful")
                logging.info("Script execution successful")

                logging.info(f"✓ {notebook_path} processed successfully")
                print(f"✓ {notebook_path} processed successfully")
                success_files.append(str(notebook_path))
            except RuntimeError as e:
                import traceback
                error_info = traceback.format_exc()
                if str(e) == "Host dependency issue":
                    host_dependency_failed_files.append((str(notebook_path), error_info))
                else:
                    python_failed_files.append((str(notebook_path), error_info))
                logging.error(f"Error processing {notebook_path}: {e}\n{error_info}")
                print(f"Error processing {notebook_path}: {e}\n{error_info}")
                print("Continuing with next file...")
                continue
            except Exception as e:
                import traceback
                error_info = traceback.format_exc()
                python_failed_files.append((str(notebook_path), error_info))
                logging.error(f"Error processing {notebook_path}: {e}\n{error_info}")
                print(f"Error processing {notebook_path}: {e}\n{error_info}")
                print("Continuing with next file...")
                continue
            finally:
                logs_dict[str(notebook_path)] = file_logs

        execution_time = time.time() - start_time
        generate_markdown_report(success_files, host_dependency_failed_files, python_failed_files, total_files, execution_time, logs_dict)

        all_failed_files = host_dependency_failed_files + python_failed_files
        if all_failed_files:
            logging.error("\nFollowing files failed:")
            print("\nFollowing files failed:")
            for file, error in all_failed_files:
                logging.error(f"- {file}: {str(error)[:50]}...")
                print(f"- {file}: {str(error)[:50]}...")
            logging.error(f"Total {len(all_failed_files)} files failed")
            print(f"Total {len(all_failed_files)} files failed")
            sys.exit(1)
        else:
            logging.info("\nAll files processed successfully!")
            print("\nAll files processed successfully!")
            sys.exit(0)
    except Exception as e:
        logging.error(f"Serious error occurred during execution: {e}")
        print(f"Serious error occurred during execution: {e}")
        sys.exit(1)
    finally:
        cleanup(env_names, NOTEBOOK_DIR)
        logging.info("\n✓ All temporary environments and files cleaned up")
        print("\n✓ All temporary environments and files cleaned up")

        images_folder = Path("images_folder")
        if images_folder.exists():
            try:
                shutil.rmtree(images_folder)
                logging.info(f"Removed images_folder: {images_folder}")
                print(f"Removed images_folder: {images_folder}")
            except Exception as e:
                logging.error(f"Failed to remove images_folder: {e}")
                print(f"Failed to remove images_folder: {e}")