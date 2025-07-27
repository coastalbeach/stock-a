@echo off
setlocal enabledelayedexpansion

:: 季度数据获取批处理程序
:: 用于获取季度的股票数据，包括季度财务报表数据、财务信号指标、行业板块数据和券商评级数据

:: 设置编码为UTF-8
chcp 65001 > nul

:: 设置标题
title 季度数据获取批处理程序

:: 设置颜色
color 0E

:: 设置路径变量
set "ROOT_DIR=%~dp0..\..\"
set "PYTHON_CMD=python"
set "LOG_DIR=%ROOT_DIR%\logs"
set "DATA_DIR=%ROOT_DIR%\data\quarterly"

:: 获取当前年月日
for /f "tokens=2 delims= " %%a in ('date /t') do set "current_date=%%a"
for /f "tokens=1-3 delims=/" %%a in ("%current_date%") do (
    set "MONTH=%%a"
    set "DAY=%%b"
    set "YEAR=%%c"
)

:: 确定当前季度
if %MONTH% LEQ 3 (
    set "QUARTER=Q1"
) else if %MONTH% LEQ 6 (
    set "QUARTER=Q2"
) else if %MONTH% LEQ 9 (
    set "QUARTER=Q3"
) else (
    set "QUARTER=Q4"
)

set "CURRENT_QUARTER=%QUARTER%_%YEAR%"

:: 创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 创建数据存储目录结构
set "QUARTER_DIR=%DATA_DIR%\%CURRENT_QUARTER%"
if not exist "%QUARTER_DIR%" mkdir "%QUARTER_DIR%"
if not exist "%QUARTER_DIR%\financial" mkdir "%QUARTER_DIR%\financial"
if not exist "%QUARTER_DIR%\analysis" mkdir "%QUARTER_DIR%\analysis"
if not exist "%QUARTER_DIR%\report" mkdir "%QUARTER_DIR%\report"

:: 设置日志文件
set "LOG_FILE=%LOG_DIR%\quarterly_data_%CURRENT_QUARTER%.log"

echo ================================================ >> "%LOG_FILE%"
echo 季度数据获取批处理程序 - %DATE% %TIME% >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

echo.
echo ================================================
echo             季度数据获取批处理程序
echo ================================================
echo 开始时间: %DATE% %TIME%
echo 数据季度: %CURRENT_QUARTER%
echo 日志文件: %LOG_FILE%
echo.
echo 正在创建数据目录...
echo.

:: 执行股票历史行情数据获取（季度）
echo 正在获取股票历史行情数据（季度）...
echo [%DATE% %TIME%] 开始获取股票历史行情数据（季度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\stock\historical_data.py" quarterly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取股票历史行情数据（季度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取股票历史行情数据（季度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取股票历史行情数据（季度）成功。
    echo [%DATE% %TIME%] 获取股票历史行情数据（季度）成功 >> "%LOG_FILE%"
)

:: 执行指数行情数据获取（季度）
echo 正在获取指数行情数据（季度）...
echo [%DATE% %TIME%] 开始获取指数行情数据（季度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\index\index_quote.py" quarterly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取指数行情数据（季度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取指数行情数据（季度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取指数行情数据（季度）成功。
    echo [%DATE% %TIME%] 获取指数行情数据（季度）成功 >> "%LOG_FILE%"
)

:: 执行季度财务报表数据获取
echo 正在获取季度财务报表数据...
echo [%DATE% %TIME%] 开始获取季度财务报表数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from fetcher.stock.financial_data import StockFinancialData; StockFinancialData().fetch_quarterly_reports()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取季度财务报表数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取季度财务报表数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取季度财务报表数据成功。
    echo [%DATE% %TIME%] 获取季度财务报表数据成功 >> "%LOG_FILE%"
)

:: 执行财务信号指标获取
echo 正在获取财务信号指标...
echo [%DATE% %TIME%] 开始获取财务信号指标 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from fetcher.stock.financial_signal import FinancialSignal; FinancialSignal().calculate_all_signals()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取财务信号指标失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取财务信号指标失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取财务信号指标成功。
    echo [%DATE% %TIME%] 获取财务信号指标成功 >> "%LOG_FILE%"
)

:: 执行板块数据获取（季度）
echo 正在获取板块数据（季度）...
echo [%DATE% %TIME%] 开始获取板块数据（季度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\market\board_realtime.py" quarterly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取板块数据（季度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取板块数据（季度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取板块数据（季度）成功。
    echo [%DATE% %TIME%] 获取板块数据（季度）成功 >> "%LOG_FILE%"
)

:: 执行行业板块数据获取
echo 正在获取行业板块数据...
echo [%DATE% %TIME%] 开始获取行业板块数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from fetcher.market.sector_data import SectorData; SectorData().fetch_all_sectors()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取行业板块数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取行业板块数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取行业板块数据成功。
    echo [%DATE% %TIME%] 获取行业板块数据成功 >> "%LOG_FILE%"
)

:: 执行龙虎榜数据获取（季度）
echo 正在获取龙虎榜数据（季度）...
echo [%DATE% %TIME%] 开始获取龙虎榜数据（季度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\trader\lhb_data.py" quarterly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取龙虎榜数据（季度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取龙虎榜数据（季度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取龙虎榜数据（季度）成功。
    echo [%DATE% %TIME%] 获取龙虎榜数据（季度）成功 >> "%LOG_FILE%"
)

:: 执行大宗交易数据获取（季度）
echo 正在获取大宗交易数据（季度）...
echo [%DATE% %TIME%] 开始获取大宗交易数据（季度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\special\block_trade.py" quarterly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取大宗交易数据（季度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取大宗交易数据（季度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取大宗交易数据（季度）成功。
    echo [%DATE% %TIME%] 获取大宗交易数据（季度）成功 >> "%LOG_FILE%"
)

:: 执行千股千评数据获取（季度）
echo 正在获取千股千评数据（季度）...
echo [%DATE% %TIME%] 开始获取千股千评数据（季度） >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\stock\stock_comment_integrated.py" quarterly >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取千股千评数据（季度）失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取千股千评数据（季度）失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取千股千评数据（季度）成功。
    echo [%DATE% %TIME%] 获取千股千评数据（季度）成功 >> "%LOG_FILE%"
)

:: 执行券商评级数据获取
echo 正在获取券商评级数据...
echo [%DATE% %TIME%] 开始获取券商评级数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% -c "from fetcher.special.stock_comment import StockComment; StockComment().fetch_broker_ratings()" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取券商评级数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取券商评级数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取券商评级数据成功。
    echo [%DATE% %TIME%] 获取券商评级数据成功 >> "%LOG_FILE%"
)

:: 生成季度汇总报告
echo 正在生成季度汇总报告...
echo [%DATE% %TIME%] 开始生成季度汇总报告 >> "%LOG_FILE%"

:: 创建季度汇总报告文件
set "REPORT_FILE=%QUARTER_DIR%\report\quarterly_summary_%CURRENT_QUARTER%.txt"

echo ================================================ > "%REPORT_FILE%"
echo              季度数据汇总报告 >> "%REPORT_FILE%"
echo ================================================ >> "%REPORT_FILE%"
echo 生成时间: %DATE% %TIME% >> "%REPORT_FILE%"
echo 数据季度: %CURRENT_QUARTER% >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 1. 季度财务报表数据 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %QUARTER_DIR%\financial >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 2. 财务信号指标 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %QUARTER_DIR%\analysis >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 3. 行业板块数据 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %QUARTER_DIR%\analysis >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo 4. 券商评级数据 >> "%REPORT_FILE%"
echo ------------------------------------------------ >> "%REPORT_FILE%"
echo 数据存储位置: %QUARTER_DIR%\analysis >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo ================================================ >> "%REPORT_FILE%"

:: 生成行业分析报告模板
set "INDUSTRY_REPORT_FILE=%QUARTER_DIR%\report\industry_analysis_%CURRENT_QUARTER%.txt"

echo ================================================ > "%INDUSTRY_REPORT_FILE%"
echo              行业分析报告模板 >> "%INDUSTRY_REPORT_FILE%"
echo ================================================ >> "%INDUSTRY_REPORT_FILE%"
echo 生成时间: %DATE% %TIME% >> "%INDUSTRY_REPORT_FILE%"
echo 数据季度: %CURRENT_QUARTER% >> "%INDUSTRY_REPORT_FILE%"
echo. >> "%INDUSTRY_REPORT_FILE%"
echo 1. 行业概览 >> "%INDUSTRY_REPORT_FILE%"
echo ------------------------------------------------ >> "%INDUSTRY_REPORT_FILE%"
echo [此处填写行业概览内容] >> "%INDUSTRY_REPORT_FILE%"
echo. >> "%INDUSTRY_REPORT_FILE%"
echo 2. 行业表现 >> "%INDUSTRY_REPORT_FILE%"
echo ------------------------------------------------ >> "%INDUSTRY_REPORT_FILE%"
echo [此处填写行业表现内容] >> "%INDUSTRY_REPORT_FILE%"
echo. >> "%INDUSTRY_REPORT_FILE%"
echo 3. 重点公司分析 >> "%INDUSTRY_REPORT_FILE%"
echo ------------------------------------------------ >> "%INDUSTRY_REPORT_FILE%"
echo [此处填写重点公司分析内容] >> "%INDUSTRY_REPORT_FILE%"
echo. >> "%INDUSTRY_REPORT_FILE%"
echo 4. 行业展望 >> "%INDUSTRY_REPORT_FILE%"
echo ------------------------------------------------ >> "%INDUSTRY_REPORT_FILE%"
echo [此处填写行业展望内容] >> "%INDUSTRY_REPORT_FILE%"
echo. >> "%INDUSTRY_REPORT_FILE%"
echo ================================================ >> "%INDUSTRY_REPORT_FILE%"

echo 季度汇总报告已生成: %REPORT_FILE%
echo 行业分析报告模板已生成: %INDUSTRY_REPORT_FILE%
echo [%DATE% %TIME%] 季度汇总报告已生成: %REPORT_FILE% >> "%LOG_FILE%"
echo [%DATE% %TIME%] 行业分析报告模板已生成: %INDUSTRY_REPORT_FILE% >> "%LOG_FILE%"

:: 完成信息
echo.
echo ================================================
echo 季度数据获取完成！
echo 结束时间: %DATE% %TIME%
echo 日志文件: %LOG_FILE%
echo 汇总报告: %REPORT_FILE%
echo 行业分析报告模板: %INDUSTRY_REPORT_FILE%
echo ================================================

echo [%DATE% %TIME%] 季度数据获取完成 >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

pause