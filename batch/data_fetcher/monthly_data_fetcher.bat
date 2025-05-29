@echo off
setlocal enabledelayedexpansion

:: 月度数据获取批处理程序
:: 用于获取月度的股票数据，包括股票基本信息、财务数据、机构持仓数据和股东数据

:: 设置编码为UTF-8
chcp 65001 > nul

:: 设置标题
title 月度数据获取批处理程序

:: 设置颜色
color 0B

:: 设置路径变量
set "ROOT_DIR=%~dp0..\..\."
set "PYTHON_CMD=python"
set "LOG_DIR=%ROOT_DIR%\logs"
set "DATA_DIR=%ROOT_DIR%\data\monthly"

:: 获取当前年月（格式：YYYYMM）
for /f "tokens=1-3 delims=/" %%a in ('%DATE%') do (
    set "DAY=%%a"
    set "MONTH=%%b"
    set "YEAR=%%c"
)
set "CURRENT_MONTH=%YEAR%%MONTH%"

:: 创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 创建数据存储目录结构
set "MONTH_DIR=%DATA_DIR%\%CURRENT_MONTH%"
if not exist "%MONTH_DIR%" mkdir "%MONTH_DIR%"
if not exist "%MONTH_DIR%\stock" mkdir "%MONTH_DIR%\stock"
if not exist "%MONTH_DIR%\financial" mkdir "%MONTH_DIR%\financial"
if not exist "%MONTH_DIR%\trader" mkdir "%MONTH_DIR%\trader"
if not exist "%MONTH_DIR%\report" mkdir "%MONTH_DIR%\report"

:: 设置日志文件
set "LOG_FILE=%LOG_DIR%\monthly_data_%CURRENT_MONTH%.log"

echo ================================================ >> "%LOG_FILE%"
echo 月度数据获取批处理程序 - %DATE% %TIME% >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

echo.
echo ================================================
echo             月度数据获取批处理程序
echo ================================================
echo 开始时间: %DATE% %TIME%
echo 数据月份: %CURRENT_MONTH%
echo 日志文件: %LOG_FILE%
echo.
echo 正在创建数据目录...
echo.

:: 执行股票基本信息获取
echo 正在获取股票基本信息...
echo [%DATE% %TIME%] 开始获取股票基本信息 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from fetcher.stock.basic_info import StockBasicInfo; StockBasicInfo().fetch_all()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取股票基本信息失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取股票基本信息失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取股票基本信息成功。
    echo [%DATE% %TIME%] 获取股票基本信息成功 >> "%LOG_FILE%"
)

:: 执行财务数据获取
echo 正在获取财务数据...
echo [%DATE% %TIME%] 开始获取财务数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from fetcher.stock.financial_data import StockFinancialData; StockFinancialData().fetch_latest_financial_data()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取财务数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取财务数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取财务数据成功。
    echo [%DATE% %TIME%] 获取财务数据成功 >> "%LOG_FILE%"
)

:: 执行机构持仓数据获取
echo 正在获取机构持仓数据...
echo [%DATE% %TIME%] 开始获取机构持仓数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from fetcher.trader.institutional import Institutional; Institutional().fetch_latest_data()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取机构持仓数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取机构持仓数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取机构持仓数据成功。
    echo [%DATE% %TIME%] 获取机构持仓数据成功 >> "%LOG_FILE%"
)

:: 执行股东数据获取
echo 正在获取股东数据...
echo [%DATE% %TIME%] 开始获取股东数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from fetcher.trader.stockholder import Stockholder; Stockholder().fetch_latest_data()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取股东数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取股东数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取股东数据成功。
    echo [%DATE% %TIME%] 获取股东数据成功 >> "%LOG_FILE%"
)

:: 执行股票历史行情数据获取（月度）
echo 正在获取股票历史行情数据（月度）...
echo [%DATE% %TIME%] 开始获取股票历史行情数据（月度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\stock\historical_data.py" monthly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取股票历史行情数据（月度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取股票历史行情数据（月度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取股票历史行情数据（月度）成功。
    echo [%DATE% %TIME%] 获取股票历史行情数据（月度）成功 >> "%LOG_FILE%"
)

:: 执行指数行情数据获取（月度）
echo 正在获取指数行情数据（月度）...
echo [%DATE% %TIME%] 开始获取指数行情数据（月度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\index\index_quote.py" monthly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取指数行情数据（月度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取指数行情数据（月度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取指数行情数据（月度）成功。
    echo [%DATE% %TIME%] 获取指数行情数据（月度）成功 >> "%LOG_FILE%"
)

:: 执行板块数据获取（月度）
echo 正在获取板块数据（月度）...
echo [%DATE% %TIME%] 开始获取板块数据（月度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\market\board_realtime.py" monthly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取板块数据（月度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取板块数据（月度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取板块数据（月度）成功。
    echo [%DATE% %TIME%] 获取板块数据（月度）成功 >> "%LOG_FILE%"
)

:: 执行龙虎榜数据获取（月度）
echo 正在获取龙虎榜数据（月度）...
echo [%DATE% %TIME%] 开始获取龙虎榜数据（月度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\trader\lhb_data.py" monthly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取龙虎榜数据（月度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取龙虎榜数据（月度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取龙虎榜数据（月度）成功。
    echo [%DATE% %TIME%] 获取龙虎榜数据（月度）成功 >> "%LOG_FILE%"
)

:: 执行大宗交易数据获取（月度）
echo 正在获取大宗交易数据（月度）...
echo [%DATE% %TIME%] 开始获取大宗交易数据（月度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\special\block_trade.py" monthly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取大宗交易数据（月度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取大宗交易数据（月度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取大宗交易数据（月度）成功。
    echo [%DATE% %TIME%] 获取大宗交易数据（月度）成功 >> "%LOG_FILE%"
)

:: 执行千股千评数据获取（月度）
echo 正在获取千股千评数据（月度）...
echo [%DATE% %TIME%] 开始获取千股千评数据（月度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\stock\stock_comment_integrated.py" monthly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取千股千评数据（月度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取千股千评数据（月度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取千股千评数据（月度）成功。
    echo [%DATE% %TIME%] 获取千股千评数据（月度）成功 >> "%LOG_FILE%"
)

:: 生成月度汇总报告
echo 正在生成月度汇总报告...
echo [%DATE% %TIME%] 开始生成月度汇总报告 >> "%LOG_FILE%"

:: 创建月度汇总报告文件
set "REPORT_FILE=%MONTH_DIR%\report\monthly_summary_%CURRENT_MONTH%.txt"

echo ================================================ > "%REPORT_FILE%"
echo              月度数据汇总报告 >> "%REPORT_FILE%"
echo ================================================ >> "%REPORT_FILE%"
echo 生成时间: %DATE% %TIME% >> "%REPORT_FILE%"
echo 数据月份: %CURRENT_MONTH% >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 1. 股票基本信息 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %MONTH_DIR%\stock >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 2. 财务数据 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %MONTH_DIR%\financial >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 3. 机构持仓数据 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %MONTH_DIR%\trader >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 4. 股东数据 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %MONTH_DIR%\trader >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo ================================================ >> "%REPORT_FILE%"

echo 月度汇总报告已生成: %REPORT_FILE%
echo [%DATE% %TIME%] 月度汇总报告已生成: %REPORT_FILE% >> "%LOG_FILE%"

:: 完成信息
echo.
echo ================================================
echo 月度数据获取完成！
echo 结束时间: %DATE% %TIME%
echo 日志文件: %LOG_FILE%
echo 汇总报告: %REPORT_FILE%
echo ================================================

echo [%DATE% %TIME%] 月度数据获取完成 >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

pause