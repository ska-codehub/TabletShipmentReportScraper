@Echo Off
echo Running...
Set "VIRTUAL_ENV=venv"
If Not Exist "%VIRTUAL_ENV%\Scripts\activate.bat" (
    echo Please Install the required library by clicking on 'install.bat'
    pause
    Exit /B 1
)
Call "%VIRTUAL_ENV%\Scripts\activate.bat"
python data_consolidate.py %*
Exit /B 0