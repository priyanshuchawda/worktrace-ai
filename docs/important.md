# Important System & Development Paths

## System Information
- **OS Name**: Microsoft Windows 11 Home
- **OS Version**: 10.0.26200
- **System Manufacturer**: Dell Inc.
- **System Model**: Inspiron 15 3520
- **System Type**: x64-based PC
- **Processor**: Intel64 Family 6 Model 154 Stepping 4 (12 logical processors)

## Key Project & Workspace Directories
- **Workspace Root**: `C:\Users\Admin\Desktop\screen-ai`
- **Temp/Cache Directory**: `C:\Users\Admin\.gemini\tmp\screen-ai`

## Essential Development Paths (from `path.md`)
The following paths are critical for building Native Windows C++ projects without relying on the Visual Studio IDE:

- **MSVC Compiler (cl.exe)**: `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.50.35717\bin\Hostx64\x64`
- **MSVC Include Directory**: `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.50.35717\include`
- **MSVC Library Directory (lib)**: `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.50.35717\lib\x64`

### Windows 10 SDK
- **SDK Base Directory**: `C:\Program Files (x86)\Windows Kits\10`
- **SDK Target Version**: `10.0.26100.0`
- **SDK Binaries (rc.exe, mt.exe, cppwinrt.exe)**: `C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64`
- **SDK Include Directories**: `C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\` (shared, ucrt, um, winrt, cppwinrt)
- **SDK Lib Directories**: `C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\` (ucrt\x64, um\x64)

### Build Utilities
- **CMake (cmake.exe)**: `C:\Program Files\CMake\bin`
- **Ninja (ninja.exe)**: `C:\Users\Admin\AppData\Local\Microsoft\WinGet\Links`

## Build Outputs (from `BUILD_NOTES.md`)
*Note: Always use the Visual Studio generator for CMake, Ninja is broken for this project due to manifest.rc failures.*
- **App (Debug)**: `build\Debug\ScreenRecorder.exe`
- **App (Release)**: `build\Release\ScreenRecorder.exe`
- **Unit Tests**: `build\tests\Debug\unit_tests.exe`

## Other Important Environment Paths
- **Project Python**: Python 3.13.12 at `C:\Python313\python.exe`
- **Project pip**: pip 26.1.1 at `C:\Python313\Lib\site-packages\pip`
- **Project Python Scripts**: `C:\Python313\Scripts\`
- **Other installed Python versions**:
  - Python 3.14 at `C:\Python314\python.exe`
  - Python 3.11 at `C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe`
- **Python launcher default**: `py` defaults to Python 3.13.12
- **PATH Python**: `where.exe python` resolves first to `C:\Python313\python.exe`
- **uv**: `uv 0.10.7`
- **Python workflow**: use `uv` by default for local-agent development.
- **uv runtime note**: plain `uv run python --version` currently resolves to Python 3.11.11, so project commands should use `uv run --python 3.13 ...` until the Python version is pinned in `services/local-agent/pyproject.toml`.
- **Python 3.13 compatibility proof**: local test environment `.venv313` successfully installed and imported FastAPI, Pydantic, SQLAlchemy, aiosqlite, pytest, ruff, pyright, Torch CPU, PaddlePaddle, PaddleOCR, and faster-whisper on Python 3.13.12.
- **Verified Python package versions from local proof**:
  - `fastapi==0.136.1`
  - `pydantic==2.13.3`
  - `sqlalchemy==2.0.49`
  - `aiosqlite==0.22.1`
  - `pytest==9.0.3`
  - `ruff==0.15.12`
  - `pyright==1.1.409`
  - `torch==2.11.0+cpu`
  - `torchvision==0.26.0+cpu`
  - `torchaudio==2.11.0+cpu`
  - `paddlepaddle==3.3.1`
  - `paddleocr==3.5.0`
  - `faster-whisper==1.2.1`
  - `onnxruntime==1.25.1`
- **Java Home**: `C:\Program Files\Eclipse Adoptium\jdk-17.0.15.6-hotspot`
- **Android Home**: `C:\Android`
- **Go Path**: `C:\Users\Admin\go`
- **NVM Home**: `C:\Users\Admin\AppData\Local\nvm`
- **VCPKG Root**: `C:\vcpkg`
- **LLVM / Clang**: `C:\Program Files\LLVM\bin`
- **PostgreSQL / GDAL / Proj**: 
  - `C:\Program Files\PostgreSQL\17\gdal-data`
  - `C:\Program Files\PostgreSQL\17\share\contrib\postgis-3.5\proj`

## Notes on Existing Documentation
- **`idea.md`**: Contains the roadmap, product definition, and AI models stack. We are currently acknowledging this file but do not need to implement the AI stack at this moment.
- **`path.md`**: Detailed C++ environment bindings.
- **`BUILD_NOTES.md`**: Troubleshooting notes for CMake and GTest compilation.
