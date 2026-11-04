# Third-party components

QuickColor uses Python and Tcl/Tk, Pillow, and pystray (with six). Windows executables are packaged using PyInstaller.

- Python: Python Software Foundation License and bundled notices.
- Tcl/Tk: their bundled licenses.
- Pillow: its bundled HPND license and applicable third-party notices.
- pystray: LGPL-3.0; the original source and license texts accompany the shared ZIP.
- six: MIT License.
- PyInstaller: GPL with the bootloader distribution exception; see its bundled license.

The Windows distribution includes license texts under `licenses/`. Dependencies are not authored by this project. No modifications were made to pystray; its version is fixed in `requirements.txt`.

To use a modified pystray with QuickColor, install the modified library into the build environment and rebuild the executable with `build.ps1` (adjust the dependency installation step to retain your modified version).
