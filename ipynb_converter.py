import json
import re
import argparse
from pathlib import Path
import sys
import ast


def is_python_code(code):
    """Check if the code is valid Python code"""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def clean_shell_commands(code):
    """Remove shell commands and system calls from the code"""
    lines = code.splitlines()
    cleaned_lines = []
    in_multi_line_string = False

    specific_shell_command_1 = '%%bash'
    specific_shell_command_2 = 'curl -L -o ~/Downloads/news-headlines-2024.zip'
    specific_shell_command_3 = 'https://www.kaggle.com/api/v1/datasets/download/dylanjcastillo/news-headlines-2024'

    for line in lines:
        # Check if inside a multi-line string
        if not in_multi_line_string:
            # Check if starting a multi-line string
            if '"""' in line or "'''" in line:
                # Simple check for same-line multi-line string termination
                if (line.count('"""') == 2 or line.count("'''") == 2):
                    cleaned_lines.append(line)
                    continue
                # Otherwise, mark as entering multi-line string
                in_multi_line_string = True
                cleaned_lines.append(line)
                continue

            # Remove specific shell commands
            if specific_shell_command_1 in line or specific_shell_command_2 in line or specific_shell_command_3 in line:
                continue

            # Remove shell magic commands
            if line.strip().startswith('!'):
                continue

            # Remove cell magic commands like %%bash
            if line.strip().startswith('%%'):
                continue

            # Remove os.system and subprocess calls
            if 'os.system(' in line or 'subprocess.' in line:
                continue

            # Keep other lines
            cleaned_lines.append(line)
        else:
            # Inside multi-line string, add directly
            cleaned_lines.append(line)
            # Check if exiting multi-line string
            if '"""' in line or "'''" in line:
                in_multi_line_string = False

    return '\n'.join(cleaned_lines)


def is_shell_magic(line):
    """Check if a line is an IPython shell magic command"""
    # Check for !-prefixed shell commands
    if line.strip().startswith('!'):
        return True
    # Check for %%bash cell magic
    if line.strip().startswith('%%bash'):
        return True
    # Check for other possible shell magics
    shell_magics = {'%%sh', '%%script sh', '%%script bash'}
    return any(magic in line for magic in shell_magics)


def is_python_exec(line):
    """Check if a line is a Python os.system or subprocess call"""
    # Check for os.system calls
    if 'os.system(' in line:
        return True
    # Check for subprocess calls
    subprocess_patterns = [
        'subprocess.run', 'subprocess.call', 'subprocess.Popen',
        'subprocess.check_call', 'subprocess.check_output'
    ]
    return any(pattern in line for pattern in subprocess_patterns)


def extract_shell_commands_from_python(code):
    """Extract shell commands from Python code"""
    commands = []
    try:
        # Parse Python code
        tree = ast.parse(code)
        # Traverse AST nodes to find shell commands
        for node in ast.walk(tree):
            # Handle os.system calls
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == 'system' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                    if node.args and isinstance(node.args[0], ast.Str):
                        commands.append(node.args[0].s)
            # Handle subprocess calls
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {'system', 'call', 'run', 'Popen', 'check_call', 'check_output'}:
                    if isinstance(node.func, ast.Attribute) and node.func.value.id == 'subprocess':
                        # Extract command argument
                        cmd_arg = None
                        if node.args:
                            cmd_arg = node.args[0]
                        elif node.keywords:
                            for kw in node.keywords:
                                if kw.arg == 'args':
                                    cmd_arg = kw.value
                                    break
                        # Extract command string
                        if cmd_arg:
                            if isinstance(cmd_arg, ast.Str):
                                commands.append(cmd_arg.s)
                            elif isinstance(cmd_arg, ast.List) and all(isinstance(e, ast.Str) for e in cmd_arg.elts):
                                # Join list arguments into a single command
                                cmd_parts = [e.s for e in cmd_arg.elts]
                                commands.append(' '.join(cmd_parts))
    except SyntaxError:
        # If parsing fails, use regex to extract commands
        os_system_pattern = re.compile(r'os\.system\(["\'](.*?)["\']\)')
        commands.extend(os_system_pattern.findall(code))

        # Simple extraction for subprocess commands
        subprocess_pattern = re.compile(r'subprocess\.(run|call|Popen|check_call|check_output)\(["\'](.*?)["\']\)')
        commands.extend(match[1] for match in subprocess_pattern.findall(code))
    return commands


def extract_shell_commands(cell_source):
    """Extract shell commands from a code cell"""
    commands = []
    lines = cell_source.splitlines()

    # Track if inside a multi-line shell magic block
    in_shell_block = False
    shell_block_lines = []

    for line in lines:
        line = line.rstrip('\n')

        # Check if starting a shell magic block
        if line.strip().startswith('%%bash') or line.strip().startswith('%%sh'):
            in_shell_block = True
            # Skip the magic command itself
            continue
        elif line.strip().startswith('%%script sh') or line.strip().startswith('%%script bash'):
            in_shell_block = True
            # Skip the magic command itself
            continue

        # If inside a shell magic block
        if in_shell_block:
            # Check if ending the block (typically next cell magic or end of file)
            if line.strip().startswith('%%'):
                in_shell_block = False
                # Process collected shell block
                if shell_block_lines:
                    commands.append('\n'.join(shell_block_lines))
                    shell_block_lines = []
                # Continue to next line
                continue
            else:
                # Collect shell command line
                shell_block_lines.append(line)
                continue

        # Process single-line shell magics
        if line.strip().startswith('!'):
            # Extract command after !
            cmd = line.strip()[1:].lstrip()
            if cmd:
                commands.append(cmd)
            continue

        # Check for shell commands in Python code
        if is_python_exec(line):
            python_commands = extract_shell_commands_from_python(line)
            commands.extend(python_commands)

    # Process the last shell block
    if shell_block_lines and in_shell_block:
        commands.append('\n'.join(shell_block_lines))

    return commands


def convert_ipynb_to_py_and_sh(ipynb_path, py_path=None, sh_path=None, add_sh_header=True):
    """Convert IPython Notebook to both Python file and Shell script"""
    # Read the IPython Notebook file
    try:
        with open(ipynb_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {ipynb_path} not found")
        return False, False

    # Determine output file paths
    if py_path is None:
        py_path = Path(ipynb_path).with_suffix('.py')
    if sh_path is None:
        sh_path = Path(ipynb_path).with_suffix('.sh')

    # Extract Python code cells
    python_code_cells = []
    shell_commands = []

    for i, cell in enumerate(notebook.get('cells', [])):
        if cell.get('cell_type') == 'code':
            source = ''.join(cell.get('source', []))

            # Extract Python code (cleaned of shell commands)
            cleaned_python_code = clean_shell_commands(source)
            if cleaned_python_code.strip():
                python_code_cells.append(cleaned_python_code)

            # Extract shell commands
            cell_shell_commands = extract_shell_commands(source)
            if cell_shell_commands:
                shell_commands.append(f"# ---- Commands from Code Cell {i+1} ----")
                shell_commands.extend(cell_shell_commands)
                shell_commands.append("")  # Add empty line

    # Write Python file
    py_success = False
    if python_code_cells:
        try:
            with open(py_path, 'w', encoding='utf-8') as f:
                f.write(f"# This Python file was converted from {Path(ipynb_path).name}\n")
                f.write("# It contains only Python code, with shell commands removed\n\n")

                for i, code in enumerate(python_code_cells):
                    if i > 0:
                        f.write("\n\n")
                    f.write(f"# ---- Code Cell {i+1} ----\n")
                    f.write(code)

            py_success = True
            print(f"Successfully created Python file: {py_path}")
        except Exception as e:
            print(f"Error creating Python file: {str(e)}")

    # Write Shell script
    sh_success = False
    if shell_commands:
        try:
            with open(sh_path, 'w', encoding='utf-8') as f:
                if add_sh_header:
                    f.write("#!/bin/bash\n")
                    f.write(f"# This Shell script was converted from {Path(ipynb_path).name}\n")
                    f.write("# It contains only shell commands extracted from code cells\n\n")

                for cmd in shell_commands:
                    f.write(f"{cmd}\n")

            # Make the script executable
            import os
            os.chmod(sh_path, os.stat(sh_path).st_mode | 0o111)

            sh_success = True
            print(f"Successfully created Shell script: {sh_path}")
        except Exception as e:
            print(f"Error creating Shell script: {str(e)}")

    if not py_success and not sh_success:
        print(f"Warning: No Python code or shell commands found in {ipynb_path}")

    return py_success, sh_success


def main():
    """Command line entry point"""
    parser = argparse.ArgumentParser(
        description='Convert IPython Notebook (.ipynb) to both Python (.py) and Shell script (.sh)')

    # Add required arguments
    parser.add_argument('input_file', help='Path to input IPython Notebook file (.ipynb)')

    # Add optional output file arguments
    parser.add_argument('-p', '--python', help='Path to output Python file, default is the same name with .py extension')
    parser.add_argument('-s', '--shell', help='Path to output Shell script file, default is the same name with .sh extension')

    # Add option to skip shell script header
    parser.add_argument('--no-sh-header', action='store_true', help='Do not add header to Shell script')

    # Add verbose mode option
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Check if input file exists and is an .ipynb file
    input_path = Path(args.input_file)

    if not input_path.exists():
        print(f"Error: File {input_path} does not exist")
        sys.exit(1)

    if input_path.suffix.lower() != '.ipynb':
        print(f"Error: Input file must be of .ipynb format, got {input_path.suffix}")
        sys.exit(1)

    # Perform the conversion
    py_success, sh_success = convert_ipynb_to_py_and_sh(
        input_path, args.python, args.shell, not args.no_sh_header
    )

    if not py_success and not sh_success:
        sys.exit(1)


if __name__ == "__main__":
    main()