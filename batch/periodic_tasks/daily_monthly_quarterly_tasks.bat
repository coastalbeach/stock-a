@echo off
setlocal enabledelayedexpansion

:: 综合任务管理批处理程序
:: 提供菜单界面，可以执行日度、月度、季度数据处理任务，或者执行所有数据处理任务，以及设置自动执行计划

:: 设置编码为UTF-8
chcp 65001 > nul

:: 设置标题
title 综合任务管理批处理程序

:: 设置颜色
color 0F

:: 设置路径变量
set "ROOT_DIR=%~dp0..\..\."
set "BATCH_DIR=%ROOT_DIR%\batch"
set "DATA_FETCHER_DIR=%BATCH_DIR%\data_fetcher"
set "SCHEDULER_DIR=%BATCH_DIR%\scheduler"

:menu
cls
echo ================================================
echo             综合任务管理批处理程序
echo ================================================
echo.
echo  [1] 执行日度数据处理任务
echo  [2] 执行月度数据处理任务
echo  [3] 执行季度数据处理任务
echo  [4] 执行所有数据处理任务
echo  [5] 设置自动执行计划
echo  [0] 退出
echo.
echo ================================================
echo.

set /p choice=请输入选项 [0-5]: 

if "%choice%"=="1" goto daily
if "%choice%"=="2" goto monthly
if "%choice%"=="3" goto quarterly
if "%choice%"=="4" goto all
if "%choice%"=="5" goto scheduler
if "%choice%"=="0" goto end

echo.
echo 无效的选项，请重新输入。
echo.
pause
goto menu

:daily
cls
echo ================================================
echo             执行日度数据处理任务
echo ================================================
echo.
echo 正在启动日度数据获取批处理程序...
echo.
start "日度数据获取" /wait "%DATA_FETCHER_DIR%\daily_data_fetcher.bat"
echo.
echo 日度数据处理任务已完成。
echo.
pause
goto menu

:monthly
cls
echo ================================================
echo             执行月度数据处理任务
echo ================================================
echo.
echo 正在启动月度数据获取批处理程序...
echo.
start "月度数据获取" /wait "%DATA_FETCHER_DIR%\monthly_data_fetcher.bat"
echo.
echo 月度数据处理任务已完成。
echo.
pause
goto menu

:quarterly
cls
echo ================================================
echo             执行季度数据处理任务
echo ================================================
echo.
echo 正在启动季度数据获取批处理程序...
echo.
start "季度数据获取" /wait "%DATA_FETCHER_DIR%\quarterly_data_fetcher.bat"
echo.
echo 季度数据处理任务已完成。
echo.
pause
goto menu

:all
cls
echo ================================================
echo             执行所有数据处理任务
echo ================================================
echo.
echo 正在启动日度数据获取批处理程序...
echo.
start "日度数据获取" /wait "%DATA_FETCHER_DIR%\daily_data_fetcher.bat"
echo.
echo 日度数据处理任务已完成。
echo.
echo 正在启动月度数据获取批处理程序...
echo.
start "月度数据获取" /wait "%DATA_FETCHER_DIR%\monthly_data_fetcher.bat"
echo.
echo 月度数据处理任务已完成。
echo.
echo 正在启动季度数据获取批处理程序...
echo.
start "季度数据获取" /wait "%DATA_FETCHER_DIR%\quarterly_data_fetcher.bat"
echo.
echo 季度数据处理任务已完成。
echo.
echo 所有数据处理任务已完成。
echo.
pause
goto menu

:scheduler
cls
echo ================================================
echo             设置自动执行计划
echo ================================================
echo.
echo 正在启动计划任务调度器...
echo.
start "计划任务调度器" "%SCHEDULER_DIR%\periodic_tasks_scheduler.bat"
echo.
pause
goto menu

:end
cls
echo ================================================
echo             感谢使用综合任务管理批处理程序
echo ================================================
echo.
echo 程序已退出。
echo.
exit /b 0