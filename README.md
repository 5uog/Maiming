<!-- FILE: README.md -->
# Ludoxel v3

Ludoxel is a PyQt6 desktop application for controlled experimentation on a restricted voxel-world model, a first-person interaction pipeline, and an OpenGL 4.3 Core Profile renderer. The present codebase contains a persistent flat sandbox, a separate Othello play space, state-dependent block-shape logic for a limited set of structural block families, and a narrowly selected native-acceleration path for arithmetic-intensive kernels. It does not presently constitute a rule-complete reproduction of Minecraft Bedrock Edition or Minecraft Java Edition, and it should not be represented as a finished system.

The repository should instead be read as an engineering workbench. The implemented systems are those that are currently useful for rendering, collision, picking, input, persistence, and deterministic numerical inspection. Where Minecraft-derived semantics are present, they are local design targets for specific subsystems rather than a claim of full game equivalence across movement, combat, world generation, inventory logic, redstone, networking, or content coverage.


## Etymology

Latin **ludus** underlies the initial element **lud-**. Its attested semantic field extends across play, game, sport, and school or training. The stem therefore bears a general ludic reference: not combat in particular, not one ruleset in particular, and not training in isolation, but play taken in its broader and more exact genus.

**Voxel** is the modern technical contraction of **volumetric** and **pixel**. In technical usage, it denotes a discrete element of three-dimensional representation, commonly treated as the spatial analogue of the pixel, and thus refers to discretized volume rather than merely to visual style or atmospheric motif.

**Ludoxel** accordingly denotes ludic activity in voxel space, or, more strictly, play conducted within a discretized volumetric world. As the title of a sandbox application, the term is exact in the only sense that matters here: the operative environment is voxel-constituted, while the activity admitted within it is ludic in a broad sense, namely as play not exhausted by any single closed game form, but proceeding through locally open course and user-directed manipulation.


## Application modes

Ludoxel currently exposes two persistent application modes inside a single desktop shell: `My World` and `Play Othello (Reversi)`.

### Switching between spaces

The pause menu exposes two persistent destinations. `Play My World` returns to the sandbox space and is disabled while that space is already active. `Play Othello (Reversi)` transfers the session into the dedicated Othello space and is disabled while the user is already there. Each space persists its own player transform and session-specific state.

### `My World`

`My World` is the ordinary persistent sandbox space. It serves as a flat inspection environment in which the implemented block subset can be placed, broken, rendered, picked, and collided against. The project includes full cubes together with several non-cubic structural forms whose render boxes, collision volumes, and pick volumes are derived from explicit block-state logic. The world model remains intentionally narrow when measured against the breadth of a complete Minecraft implementation. 

Within this space, the ordinary block interaction path remains active. The block inventory is opened with `E`, world edits persist with the sandbox space, and re-entering the space restores the previous player transform together with local world modifications.

### `Play Othello (Reversi)`

`Play Othello (Reversi)` is a second persistent play space hosted inside the same application shell. It has its own hotbar, match settings, AI opponent, clocks, board interaction path, piece animation path, and rendering path. This mode is a specialized subsystem layered onto the renderer and UI framework. It should be understood as a self-contained application mode rather than as evidence that the surrounding sandbox has reached general game completeness. 

Within this space, block placement, block breaking, and the block inventory overlay are disabled. The Othello hotbar is reserved for control items. Slot `1` contains `Start`, and slot `9` contains `Settings`. Right-clicking `Start` begins a fresh match or restarts the current match under the stored defaults. Right-clicking `Settings` opens the Othello settings dialog, which configures AI strength, time control, and player order for the next match. The default Othello configuration is `Medium`, `20 minutes per side`, and `player moves first`.

Disc placement is performed by aiming at a highlighted legal square and pressing the left mouse button. The rendered board is hosted in a separate persistent world space, the match clocks pause while the pause menu or the Othello settings dialog is open, and centered status text is used for AI-thinking, pass, and result states.


## Source layout and execution model

The repository intentionally preserves the existing `python -m main` startup route. `main.py` prepends `src` to `sys.path`, after which control passes into the package entry path under `ludoxel.api`. The public project title is **Ludoxel**, whereas the current source package and import namespace remain `ludoxel`. This separation is intentional at the present stage and allows the visible application identity to evolve without forcing an immediate package-level rename across the codebase.

The native build remains deliberately narrow. Only `ludoxel.core.geometry.intersection`, `ludoxel.core.grid.voxel_dda`, and `ludoxel.core.math.view_angles` are compiled in place. Those modules are dominated by scalar arithmetic, geometric branching, and dense numerical work. Broader scene and block orchestration layers remain in Python because they are governed primarily by Python object traffic, callback dispatch, dictionary access, and heterogeneous container traversal, all of which reduce the benefit of opaque extension-module compilation and can worsen end-to-end frame cost when moved wholesale across the extension boundary.

The editable install and the explicit native build are intentionally separated. The editable install makes the source tree importable for development. The explicit `build_ext --inplace` path performs the optional native compilation step. This separation prevents editable-install metadata evaluation from depending on Cython at the moment when development dependencies may not yet be installed.


## Development workflow

The development path described below assumes Python 3.14.x, PyQt6 6.6 or newer, NumPy 1.26 or newer, PyOpenGL 3.1.7 or newer, and a working OpenGL 4.3 Core Profile context. On Windows, the Microsoft Visual Studio Build Tools C++ workload is assumed to already be installed before any local native build is attempted.

The following sequence is the intended Windows development path for a clean environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]" --no-build-isolation
python .\setup.py build_ext --inplace
python -c "import ludoxel.core.geometry.intersection as m; print(m.__file__)"
python -c "import ludoxel.core.grid.voxel_dda as m; print(m.__file__)"
python -c "import ludoxel.core.math.view_angles as m; print(m.__file__)"
python -m main
```

After the in-place native build has completed on Windows, the three verification commands above should resolve to `.pyd` files rather than the corresponding `.py` sources. If the native build is not required for the task at hand, the application can still be launched through `python -m main` after the editable install.

If one of the native-accelerated modules is edited, rerun the in-place extension build.

```powershell
python .\setup.py build_ext --inplace
```

If packaging metadata, dependency declarations, entry-point definitions, or package-data rules are changed, rerun the editable install as well.

```powershell
python -m pip install -e ".[dev]" --no-build-isolation
```

On Windows, a loaded `.pyd` file cannot be overwritten while a Python process still holds the module image open. If `build_ext --inplace` fails with a file-in-use or permission error, terminate the running application and any interactive Python processes that imported the target module, then rerun the build.

```powershell
taskkill /F /IM python.exe
python .\setup.py build_ext --inplace
```

Standard source and wheel packaging remains available through the ordinary frontend.

```powershell
python -m build
```

That packaging path is intentionally distinct from the explicit local optimization path. The repository does not make Cython execution an implicit side effect of every packaging or installation action. Native compilation remains an explicit developer decision.