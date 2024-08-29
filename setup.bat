rem Create and enter a temporary directory.
cd %TMP%
IF EXIST BATTALION_BUNDLE_TMP rmdir /s /q BATTALION_BUNDLE_TMP
mkdir BATTALION_BUNDLE_TMP
cd BATTALION_BUNDLE_TMP

rem Create a virtual environment.
set PYTHONNOUSERSITE=1
set "PYTHONPATH="
python -m venv venv
call venv/Scripts/activate.bat

rem Install cx_Freeze and its dependencies.
python -m pip install cx-Freeze==6.15.10 cx-Logging==3.1.0 lief==0.13.2

rem Retrieve a fresh checkout from the repository to avoid a potentially
rem polluted local checkout.
git clone https://github.com/RenolY2/battalion-level-editor.git
cd battalion-level-editor

rem Install the application's dependencies.
python -m pip install -r requirements.txt

rem Build the bundle.
python setup.py build

rem Open directory in file explorer.
cd build
start .
pause