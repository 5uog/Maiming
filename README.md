<!-- FILE: README.md -->
# Maiming v2.5

Maiming is a deterministic Bedrock-movement sandbox and OpenGL 4.3 Core Profile desktop renderer for block-accurate Minecraft PvP aiming studies. The current development layout intentionally preserves the existing `python -m main` startup route while allowing a narrowly selected subset of arithmetic-dominant modules to be compiled in place as native extension modules. The generated C sources are emitted under `build/cython`, while the compiled extension binaries are emitted under the ordinary package paths inside `src/maiming` so that the normal import graph continues to work without any entry-point change.

## Runtime assumptions

This repository assumes Python 3.14.x, PyQt6 6.6 or newer, NumPy 1.26 or newer, PyOpenGL 3.1.7 or newer, and an OpenGL 4.3 Core Profile context. On Windows, the Visual Studio Build Tools C++ workload is assumed to be already installed.

## Why the Cython target set is intentionally narrow

The native build is intentionally restricted to `maiming.core.geometry.intersection`, `maiming.core.grid.voxel_dda`, and `maiming.core.math.view_angles`. These modules are dominated by scalar arithmetic, geometric branching, and tight per-call numerical work. By contrast, the scene-assembly and block-shape traversal layers are dominated by Python object traffic, Python callback dispatch, dictionary access, dataclass materialization, and heterogeneous container iteration. Compiling those broader layers as opaque extension modules did not reduce semantic work, but it did add extension-boundary overhead and worsened frame time in practice. The current build therefore keeps the callback-heavy orchestration layers in Python and compiles only the arithmetic-dominant leaf modules.

## Why the editable install is separated from the native build

The editable install and the native extension build are intentionally separated. The editable install is responsible for making the source tree importable in development, while the native build is responsible for compiling the selected extension targets in place. This separation is necessary because the metadata phase of an editable install may evaluate `setup.py` before optional development dependencies have been installed. Therefore the metadata path must not require Cython, while the explicit `build_ext --inplace` path may require it.

## First-time setup

Create and activate a virtual environment, then upgrade the packaging toolchain.

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip setuptools wheel

Install the editable package together with the development dependencies.

    python -m pip install -e ".[dev]" --no-build-isolation

That command is expected to succeed before any local native build is attempted.

## Building the native extensions in place

After the editable install has completed, build the selected native modules directly into the source tree.

    python .\setup.py build_ext --inplace

If compiler-side parallelism is desired, pass it to `build_ext`.

    python .\setup.py build_ext --inplace -j 4

The setup script intentionally keeps Cython-side parallel fan-out disabled so that the Windows multiprocessing spawn problem is not introduced by the build script itself.

## Verifying that the compiled modules are the ones being imported

The development layout is designed so that the compiled extension binaries shadow the corresponding Python source modules at import time when both are present under the same package path. The following commands can be used to confirm that the import resolver is selecting the compiled artifacts rather than the `.py` files.

    python -c "import maiming.core.geometry.intersection as m; print(m.__file__)"
    python -c "import maiming.core.grid.voxel_dda as m; print(m.__file__)"
    python -c "import maiming.core.math.view_angles as m; print(m.__file__)"

On Windows, each printed path should resolve to a `.pyd` file after the in-place native build has completed.

## Running the application

After the in-place native build has completed, keep using the existing startup command.

    python -m main

This works because `main.py` prepends `src` to `sys.path`, and the compiled extension modules are emitted in place under that same source tree.

## Rebuild rules during development

If one of the native-accelerated modules is edited, rebuild the extensions again.

    python .\setup.py build_ext --inplace

If installation metadata, dependency declarations, entry points, or package-data rules are changed, rerun the editable install as well.

    python -m pip install -e ".[dev]" --no-build-isolation

## Windows `.pyd` lock handling

On Windows, a loaded `.pyd` file cannot be overwritten while a Python process still holds it. If `build_ext --inplace` fails with a permission error or file-in-use error, close the running application, close interactive Python sessions, close IDE-integrated Python processes, and then rerun the build.

    taskkill /F /IM python.exe
    python .\setup.py build_ext --inplace

If a specific compiled module is still locked after the application window has already been closed, close the terminal or IDE process that imported it, delete the locked `.pyd` if necessary, and rerun the same command.

## Building distribution artifacts

The standard frontend remains available for packaging the Python source tree and bundled assets.

    python -m build

The explicit local optimization path, however, is intentionally the in-place `build_ext` command shown above. The project keeps editable-install metadata evaluation decoupled from mandatory Cython execution, and the native developer path is therefore an explicit step rather than an implicit side effect of every packaging command.

## Development summary

The intended Windows development sequence is the following.

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -e ".[dev]" --no-build-isolation
    python .\setup.py build_ext --inplace
    python -c "import maiming.core.grid.voxel_dda as m; print(m.__file__)"
    python -m main