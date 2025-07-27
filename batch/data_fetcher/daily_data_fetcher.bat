@echo off
setlocal enabledelayedexpansion

:: 日度数据获取批处理程序
:: 用于获取每日的股票数据，包括股票行情、指数行情、板块数据、龙虎榜等

:: 设置编码为UTF-8
chcp 65001 > nul

:: 设置标题
title 日度数据获取批处理程序

:: 设置颜色
color 0A

:: 设置路径变量
set "ROOT_DIR=%~dp0..\..\"
set "PYTHON_CMD=python"
set "LOG_DIR=%ROOT_DIR%\logs"
set "DATA_DIR=%ROOT_DIR%\data\daily"

:: 获取当前日期（格式：YYYYMMDD）
for /f "tokens=2 delims= " %%a in ('date /t') do set "current_date=%%a"
for /f "tokens=1-3 delims=/" %%a in ("%current_date%") do (
    set "MONTH=%%a"
    set "DAY=%%b"
    set "YEAR=%%c"
)

:: 补零处理
if %MONTH% LSS 10 set "MONTH=0%MONTH%"
if %DAY% LSS 10 set "DAY=0%DAY%"
set "TODAY=%YEAR%%MONTH%%DAY%"

:: 创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 创建数据存储目录结构
set "TODAY_DIR=%DATA_DIR%\%TODAY%"
if not exist "%TODAY_DIR%" mkdir "%TODAY_DIR%"
if not exist "%TODAY_DIR%\stock" mkdir "%TODAY_DIR%\stock"
if not exist "%TODAY_DIR%\index" mkdir "%TODAY_DIR%\index"
if not exist "%TODAY_DIR%\market" mkdir "%TODAY_DIR%\market"
if not exist "%TODAY_DIR%\special" mkdir "%TODAY_DIR%\special"

:: 设置日志文件
set "LOG_FILE=%LOG_DIR%\daily_data_%TODAY%.log"

echo ================================================ >> "%LOG_FILE%"
echo 日度数据获取批处理程序 - %DATE% %TIME% >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

echo.
echo ================================================
echo             日度数据获取批处理程序
echo ================================================
echo 开始时间: %DATE% %TIME%
echo 数据日期: %TODAY%
echo 日志文件: %LOG_FILE%
echo.
echo 正在创建数据目录...
echo.

:: 执行股票历史行情数据获取
echo 正在获取股票历史行情数据...
echo [%DATE% %TIME%] 开始获取股票历史行情数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\stock\historical_data.py" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取股票历史行情数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取股票历史行情数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取股票历史行情数据成功。
    echo [%DATE% %TIME%] 获取股票历史行情数据成功 >> "%LOG_FILE%"
)

:: 执行指数行情数据获取
echo 正在获取指数行情数据...
echo [%DATE% %TIME%] 开始获取指数行情数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\index\index_quote.py" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取指数行情数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取指数行情数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取指数行情数据成功。
    echo [%DATE% %TIME%] 获取指数行情数据成功 >> "%LOG_FILE%"
)

:: 执行板块数据获取
echo 正在获取板块数据...
echo [%DATE% %TIME%] 开始获取板块数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\market\sector_data.py" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取板块数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取板块数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取板块数据成功。
    echo [%DATE% %TIME%] 获取板块数据成功 >> "%LOG_FILE%"
)

:: 执行龙虎榜数据获取
echo 正在获取龙虎榜数据...
echo [%DATE% %TIME%] 开始获取龙虎榜数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\trader\lhb_data.py" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取龙虎榜数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取龙虎榜数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取龙虎榜数据成功。
    echo [%DATE% %TIME%] 获取龙虎榜数据成功 >> "%LOG_FILE%"
)

:: 执行大宗交易数据获取
echo 正在获取大宗交易数据...
echo [%DATE% %TIME%] 开始获取大宗交易数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\special\block_trade.py" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取大宗交易数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取大宗交易数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取大宗交易数据成功。
    echo [%DATE% %TIME%] 获取大宗交易数据成功 >> "%LOG_FILE%"
)

:: 执行千股千评数据获取
echo 正在获取千股千评数据...
echo [%DATE% %TIME%] 开始获取千股千评数据 >> "%LOG_FILE%"
cd /d "%ROOT_DIR%"
%PYTHON_CMD% "%ROOT_DIR%\fetcher\stock\stock_comment_integrated.py" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 获取千股千评数据失败，请查看日志文件。
    echo [%DATE% %TIME%] 获取千股千评数据失败，错误代码: %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo 获取千股千评数据成功。
    echo [%DATE% %TIME%] 获取千股千评数据成功 >> "%LOG_FILE%"
)

:: 完成信息
echo.
echo ================================================
echo 日度数据获取完成！
echo 结束时间: %DATE% %TIME%
echo 日志文件: %LOG_FILE%
echo ================================================

echo [%DATE% %TIME%] 日度数据获取完成 >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

pause