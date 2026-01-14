"""
Compile Vyper contracts and save ABI.
"""

import json
import subprocess
from pathlib import Path


def compile_contract():
    """Compile ApprovalInspector contract."""
    contracts_dir = Path(__file__).parent.parent
    src_dir = contracts_dir / "src"
    abi_dir = contracts_dir / "abi"

    # Create abi directory if it doesn't exist
    abi_dir.mkdir(exist_ok=True)

    contract_path = src_dir / "ApprovalInspector.vy"

    if not contract_path.exists():
        print(f"Contract not found: {contract_path}")
        return

    print(f"Compiling {contract_path}...")

    try:
        # Compile with vyper
        result = subprocess.run(
            ["vyper", str(contract_path), "-f", "abi"],
            capture_output=True,
            text=True,
            check=True,
        )

        abi = json.loads(result.stdout)

        # Save ABI
        abi_path = abi_dir / "ApprovalInspector.json"
        with open(abi_path, "w") as f:
            json.dump(abi, f, indent=2)

        print(f"✓ ABI saved to {abi_path}")

        # Get bytecode
        result = subprocess.run(
            ["vyper", str(contract_path)], capture_output=True, text=True, check=True
        )

        bytecode = result.stdout.strip()

        # Save bytecode
        bytecode_path = abi_dir / "ApprovalInspector.bin"
        with open(bytecode_path, "w") as f:
            f.write(bytecode)

        print(f"✓ Bytecode saved to {bytecode_path}")
        print(f"✓ Compilation successful!")

    except subprocess.CalledProcessError as e:
        print(f"Compilation failed: {e.stderr}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    compile_contract()
