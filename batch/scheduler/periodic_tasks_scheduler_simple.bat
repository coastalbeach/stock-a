@echo off
setlocal enabledelayedexpansion

:: Simple Periodic Task Scheduler
title Task Scheduler
color 0A

:: Set path variables
set "ROOT_DIR=%~dp0..\..\"
set "BATCH_DIR=%ROOT_DIR%\batch"
set "DATA_FETCHER_DIR=%BATCH_DIR%\data_fetcher"
set "TASK_PREFIX=StockA_"

:menu
cls
echo ================================================
echo            Task Scheduler
echo ================================================
echo.
echo  [1] Set Daily Task
echo  [2] Set Weekly Task  
echo  [3] Set Monthly Task
echo  [4] Set Quarterly Task
echo  [5] View Tasks
echo  [6] Delete Task
echo  [0] Exit
echo.
echo ================================================
echo.
set /p "choice=Enter option [0-6]: "

if "%choice%"=="1" goto daily
if "%choice%"=="2" goto weekly
if "%choice%"=="3" goto monthly
if "%choice%"=="4" goto quarterly
if "%choice%"=="5" goto view
if "%choice%"=="6" goto delete
if "%choice%"=="0" goto end
echo Invalid option!
pause
goto menu

:daily
cls
echo Setting Daily Data Fetching Task...
echo.
set /p "time=Enter time (HH:MM format, e.g., 09:00): "
if "%time%"=="" (
    echo Time cannot be empty!
    pause
    goto daily
)
schtasks /create /tn "%TASK_PREFIX%DailyData" /tr "\"%DATA_FETCHER_DIR%\daily_data_fetcher.bat\"" /sc daily /st %time% /f
if %errorlevel%==0 (
    echo Daily task created successfully!
) else (
    echo Failed to create daily task!
)
pause
goto menu

:weekly
cls
echo Setting Weekly Data Fetching Task...
echo.
set /p "day=Enter day (MON/TUE/WED/THU/FRI/SAT/SUN): "
set /p "time=Enter time (HH:MM format): "
if "%day%"=="" (
    echo Day cannot be empty!
    pause
    goto weekly
)
if "%time%"=="" (
    echo Time cannot be empty!
    pause
    goto weekly
)
schtasks /create /tn "%TASK_PREFIX%WeeklyData" /tr "\"%DATA_FETCHER_DIR%\weekly_data_fetcher.bat\"" /sc weekly /d %day% /st %time% /f
if %errorlevel%==0 (
    echo Weekly task created successfully!
) else (
    echo Failed to create weekly task!
)
pause
goto menu

:monthly
cls
echo Setting Monthly Data Fetching Task...
echo.
set /p "day=Enter day of month (1-31): "
set /p "time=Enter time (HH:MM format): "
if "%day%"=="" (
    echo Day cannot be empty!
    pause
    goto monthly
)
if "%time%"=="" (
    echo Time cannot be empty!
    pause
    goto monthly
)
schtasks /create /tn "%TASK_PREFIX%MonthlyData" /tr "\"%DATA_FETCHER_DIR%\monthly_data_fetcher.bat\"" /sc monthly /d %day% /st %time% /f
if %errorlevel%==0 (
    echo Monthly task created successfully!
) else (
    echo Failed to create monthly task!
)
pause
goto menu

:quarterly
cls
echo Setting Quarterly Data Fetching Task...
echo.
set /p "month=Enter start month (1/4/7/10): "
set /p "day=Enter day of month (1-31): "
set /p "time=Enter time (HH:MM format): "
if "%month%"=="" (
    echo Month cannot be empty!
    pause
    goto quarterly
)
if "%day%"=="" (
    echo Day cannot be empty!
    pause
    goto quarterly
)
if "%time%"=="" (
    echo Time cannot be empty!
    pause
    goto quarterly
)
if "%month%"=="1" set "months=JAN,APR,JUL,OCT"
if "%month%"=="4" set "months=APR,JUL,OCT,JAN"
if "%month%"=="7" set "months=JUL,OCT,JAN,APR"
if "%month%"=="10" set "months=OCT,JAN,APR,JUL"
if not defined months (
    echo Invalid month! Please enter 1, 4, 7, or 10.
    pause
    goto quarterly
)
schtasks /create /tn "%TASK_PREFIX%QuarterlyData" /tr "\"%DATA_FETCHER_DIR%\quarterly_data_fetcher.bat\"" /sc monthly /mo 3 /d %day% /st %time% /f
if %errorlevel%==0 (
    echo Quarterly task created successfully!
) else (
    echo Failed to create quarterly task!
)
pause
goto menu

:view
cls
echo Current Scheduled Tasks:
echo ================================================
schtasks /query /tn "%TASK_PREFIX%*" /fo table
echo ================================================
pause
goto menu

:delete
cls
echo Current Tasks:
schtasks /query /tn "%TASK_PREFIX%*" /fo list
echo.
set /p "taskname=Enter task name to delete (without prefix): "
if "%taskname%"=="" (
    echo Task name cannot be empty!
    pause
    goto delete
)
schtasks /delete /tn "%TASK_PREFIX%%taskname%" /f
if %errorlevel%==0 (
    echo Task deleted successfully!
) else (
    echo Failed to delete task or task not found!
)
pause
goto menu

:end
echo Exiting...
exit /b 0