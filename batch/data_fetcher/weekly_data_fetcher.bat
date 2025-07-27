@echo off
setlocal enabledelayedexpansion

:: 周度数据获取批处理程序
:: 用于获取每周的股票数据，包括股票技术分析、周线数据、市场趋势分析等

:: 设置编码为UTF-8
chcp 65001 > nul

:: 设置标题
title 周度数据获取批处理程序

:: 设置颜色
color 0C

:: 设置路径变量
set "ROOT_DIR=%~dp0..\..\"
set "PYTHON_CMD=python"
set "LOG_DIR=%ROOT_DIR%\logs"
set "DATA_DIR=%ROOT_DIR%\data\weekly"

:: 获取当前日期
for /f "tokens=2 delims= " %%a in ('date /t') do set "current_date=%%a"
for /f "tokens=1-3 delims=/" %%a in ("%current_date%") do (
    set "MONTH=%%a"
    set "DAY=%%b"
    set "YEAR=%%c"
)

:: 补零处理
if %MONTH% LSS 10 set "MONTH=0%MONTH%"
if %DAY% LSS 10 set "DAY=0%DAY%"

:: 计算当前周（简化为年+月+第几周）
set /a WEEK_NUM=(%DAY%-1)/7+1
set "CURRENT_WEEK=%YEAR%%MONTH%W%WEEK_NUM%"

:: 创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 创建数据存储目录结构
set "WEEK_DIR=%DATA_DIR%\%CURRENT_WEEK%"
if not exist "%WEEK_DIR%" mkdir "%WEEK_DIR%"
if not exist "%WEEK_DIR%\stock" mkdir "%WEEK_DIR%\stock"
if not exist "%WEEK_DIR%\index" mkdir "%WEEK_DIR%\index"
if not exist "%WEEK_DIR%\market" mkdir "%WEEK_DIR%\market"
if not exist "%WEEK_DIR%\analysis" mkdir "%WEEK_DIR%\analysis"
if not exist "%WEEK_DIR%\report" mkdir "%WEEK_DIR%\report"

:: 设置日志文件
set "LOG_FILE=%LOG_DIR%\weekly_data_%CURRENT_WEEK%.log"

echo ================================================ >> "%LOG_FILE%"
echo 周度数据获取批处理程序 - %DATE% %TIME% >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

echo.
echo ================================================
echo             周度数据获取批处理程序
echo ================================================
echo 开始时间: %DATE% %TIME%
echo 数据周期: %CURRENT_WEEK%
echo 日志文件: %LOG_FILE%
echo.
echo 正在创建数据目录...
echo.

:: 执行股票周线数据获取
echo 正在获取股票周线数据...
echo [%DATE% %TIME%] 开始获取股票周线数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\stock\historical_data.py" weekly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取股票周线数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取股票周线数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取股票周线数据成功。
    echo [%DATE% %TIME%] 获取股票周线数据成功 >> "%LOG_FILE%"
)

:: 执行指数周线数据获取
echo 正在获取指数周线数据...
echo [%DATE% %TIME%] 开始获取指数周线数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\index\index_quote.py" weekly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取指数周线数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取指数周线数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取指数周线数据成功。
    echo [%DATE% %TIME%] 获取指数周线数据成功 >> "%LOG_FILE%"
)

:: 执行板块周度数据获取
echo 正在获取板块周度数据...
echo [%DATE% %TIME%] 开始获取板块周度数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\market\sector_data.py" weekly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取板块周度数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取板块周度数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取板块周度数据成功。
    echo [%DATE% %TIME%] 获取板块周度数据成功 >> "%LOG_FILE%"
)

:: 执行技术指标分析
echo 正在执行技术指标分析...
echo [%DATE% %TIME%] 开始执行技术指标分析 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from core.analyzer.technical_indicators import TechnicalIndicators; TechnicalIndicators().run_weekly_analysis()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 技术指标分析失败，请查看日志文件。
    echo [%DATE% %TIME%] 技术指标分析失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 技术指标分析成功。
    echo [%DATE% %TIME%] 技术指标分析成功 >> "%LOG_FILE%"
)

:: 执行市场趋势分析
echo 正在执行市场趋势分析...
echo [%DATE% %TIME%] 开始执行市场趋势分析 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from fetcher.market.trend_analysis import TrendAnalysis; TrendAnalysis().run_weekly_analysis()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 市场趋势分析失败，请查看日志文件。
    echo [%DATE% %TIME%] 市场趋势分析失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 市场趋势分析成功。
    echo [%DATE% %TIME%] 市场趋势分析成功 >> "%LOG_FILE%"
)

:: 生成周度汇总报告
echo 正在生成周度汇总报告...
echo [%DATE% %TIME%] 开始生成周度汇总报告 >> "%LOG_FILE%"

:: 创建周度汇总报告文件
set "REPORT_FILE=%WEEK_DIR%\report\weekly_summary_%CURRENT_WEEK%.txt"

echo ================================================ > "%REPORT_FILE%"
echo              周度数据汇总报告 >> "%REPORT_FILE%"
echo ================================================ >> "%REPORT_FILE%"
echo 生成时间: %DATE% %TIME% >> "%REPORT_FILE%"
echo 数据周期: %CURRENT_WEEK% >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 1. 股票周线数据 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %WEEK_DIR%\stock >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 2. 指数周线数据 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %WEEK_DIR%\index >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 3. 板块周度数据 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %WEEK_DIR%\market >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 4. 技术指标分析 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %WEEK_DIR%\analysis >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 5. 市场趋势分析 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %WEEK_DIR%\analysis >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo ================================================ >> "%REPORT_FILE%"

echo 周度汇总报告已生成: %REPORT_FILE%
echo [%DATE% %TIME%] 周度汇总报告已生成: %REPORT_FILE% >> "%LOG_FILE%"

:: 完成信息
echo.
echo ================================================
echo 周度数据获取完成！
echo 结束时间: %DATE% %TIME%
echo 日志文件: %LOG_FILE%
echo 汇总报告: %REPORT_FILE%
echo ================================================

echo [%DATE% %TIME%] 周度数据获取完成 >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

pause