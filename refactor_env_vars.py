import os
import sys
import re
from dotenv import load_dotenv
from openai import OpenAI

def split_into_cells(original_code: str) -> list[tuple[str, str]]:
    """Split code into cells using the cell delimiter pattern"""
    cell_pattern = r'^# ---- Code Cell \d+ ----$'
    cells = re.split(cell_pattern, original_code, flags=re.MULTILINE)
    headers = re.findall(cell_pattern, original_code, flags=re.MULTILINE)
    return list(zip(headers, cells))

def process_api_cell(header: str, cell_content: str, env_vars: str) -> str:
    """Process a single cell containing API-related code"""
    if 'API' not in cell_content.upper():
        return f"{header}{cell_content}"
    
    code = '\n'.join([line for line in cell_content.strip().split('\n') if line.strip()])
    
    prompt = f"""
You are a Python code refactoring engineer. Refactor the following code cell to use environment variables from a .env file:
1. Replace hardcoded API keys with `os.getenv('VAR_NAME')`
2. Add necessary imports (e.g., `from dotenv import load_dotenv` if missing)
3. **Strictly preserve the original cell structure and comments**
4. Use these environment variables: {env_vars}

Cell code:
```python
{code}
```
Return ONLY the modified cell code (including header and comments), no additional text:
"""
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1000
    )
    modified_code = response.choices[0].message.content.strip()
    # Remove markdown code block wrappers if present
    if modified_code.startswith('```python'):
        modified_code = modified_code[9:-3].strip()

    return f"{header}\n{modified_code}\n"

def refactor_code() -> str:
    """Main refactoring logic"""
    load_dotenv()
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY is not set in .env file.")
        sys.exit(1)

    if len(sys.argv) != 2:
        print("Usage: python refactor_env_vars.py <path_to_python_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    with open(input_file, 'r') as f:
        original_code = f.read()

    env_vars = os.getenv('ENV_VARS', '')
    if not env_vars:
        print("ERROR: ENV_VARS is not set in .env file.")
        sys.exit(1)

    cells = split_into_cells(original_code)
    modified_cells = []

    for header, content in cells:
        processed_cell = process_api_cell(header, content, env_vars)
        modified_cells.append(processed_cell)

    return ''.join(modified_cells)

if __name__ == "__main__":
    modified_code = refactor_code()
    print(modified_code)
