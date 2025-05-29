@echo off
setlocal enabledelayedexpansion

:: 计划任务调度器
:: 用于设置Windows计划任务，实现数据获取的自动化执行

:: 设置编码为UTF-8
chcp 65001 > nul

:: 设置标题
title 计划任务调度器

:: 设置颜色
color 0D

:: 设置路径变量
set "ROOT_DIR=%~dp0..\..\."
set "BATCH_DIR=%ROOT_DIR%\batch"
set "DATA_FETCHER_DIR=%BATCH_DIR%\data_fetcher"

:: 设置任务名称前缀
set "TASK_PREFIX=StockA_"

:menu
cls
echo ================================================
echo                计划任务调度器
echo ================================================
echo.
echo  [1] 设置日度数据获取任务
echo  [2] 设置月度数据获取任务
echo  [3] 设置季度数据获取任务
echo  [4] 查看已设置的计划任务
echo  [5] 删除计划任务
echo  [0] 返回主菜单
echo.
echo ================================================
echo.

set /p choice=请输入选项 [0-5]: 

if "%choice%"=="1" goto daily
if "%choice%"=="2" goto monthly
if "%choice%"=="3" goto quarterly
if "%choice%"=="4" goto view
if "%choice%"=="5" goto delete
if "%choice%"=="0" goto end

echo.
echo 无效的选项，请重新输入。
echo.
pause
goto menu

:daily
cls
echo ================================================
echo             设置日度数据获取任务
echo ================================================
echo.
echo 请选择执行频率：
echo  [1] 每天执行
echo  [2] 工作日执行（周一至周五）
echo  [3] 自定义日期执行
echo  [0] 返回上级菜单
echo.
echo ================================================
echo.

set /p daily_choice=请输入选项 [0-3]: 

if "%daily_choice%"=="1" goto daily_everyday
if "%daily_choice%"=="2" goto daily_workday
if "%daily_choice%"=="3" goto daily_custom
if "%daily_choice%"=="0" goto menu

echo.
echo 无效的选项，请重新输入。
echo.
pause
goto daily

:daily_everyday
set "TASK_NAME=%TASK_PREFIX%Daily_Everyday"
set "TASK_DESC=每天执行日度数据获取任务"
set "SCHEDULE_TYPE=DAILY"
goto set_daily_time

:daily_workday
set "TASK_NAME=%TASK_PREFIX%Daily_Workday"
set "TASK_DESC=工作日执行日度数据获取任务"
set "SCHEDULE_TYPE=WEEKLY"
set "DAYS=MON,TUE,WED,THU,FRI"
goto set_daily_time

:daily_custom
cls
echo ================================================
echo             设置自定义日期执行
echo ================================================
echo.
echo 请选择执行日期（多选请用逗号分隔，如：MON,WED,FRI）：
echo  MON - 周一
echo  TUE - 周二
echo  WED - 周三
echo  THU - 周四
echo  FRI - 周五
echo  SAT - 周六
echo  SUN - 周日
echo.

set /p DAYS=请输入执行日期: 

set "TASK_NAME=%TASK_PREFIX%Daily_Custom"
set "TASK_DESC=自定义日期执行日度数据获取任务"
set "SCHEDULE_TYPE=WEEKLY"

:set_daily_time
cls
echo ================================================
echo             设置执行时间
echo ================================================
echo.
echo 请输入执行时间（24小时制，格式：HH:MM）：
echo 例如：16:30 表示下午4点30分
echo.

set /p EXEC_TIME=请输入执行时间: 

:: 验证时间格式
echo %EXEC_TIME% | findstr /r /c:"^[0-2][0-9]:[0-5][0-9]$" > nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 时间格式无效，请使用 HH:MM 格式（24小时制）。
    echo.
    pause
    goto set_daily_time
)

:: 提取小时和分钟
for /f "tokens=1,2 delims=:" %%a in ("%EXEC_TIME%") do (
    set "HOUR=%%a"
    set "MINUTE=%%b"
)

:: 验证小时是否有效
if %HOUR% GTR 23 (
    echo.
    echo 小时必须在 0-23 之间。
    echo.
    pause
    goto set_daily_time
)

:: 创建计划任务
cls
echo ================================================
echo             创建计划任务
echo ================================================
echo.
echo 任务名称: %TASK_NAME%
echo 任务描述: %TASK_DESC%
echo 执行时间: %EXEC_TIME%
echo.

if "%SCHEDULE_TYPE%"=="DAILY" (
    schtasks /create /tn "%TASK_NAME%" /tr "\"%DATA_FETCHER_DIR%\daily_data_fetcher.bat\"" /sc DAILY /st %EXEC_TIME% /f /rl HIGHEST /ru "SYSTEM" /d "*" /np
) else (
    schtasks /create /tn "%TASK_NAME%" /tr "\"%DATA_FETCHER_DIR%\daily_data_fetcher.bat\"" /sc WEEKLY /st %EXEC_TIME% /f /rl HIGHEST /ru "SYSTEM" /d %DAYS% /np
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 创建计划任务失败，请检查是否有管理员权限。
    echo.
) else (
    echo.
    echo 计划任务创建成功！
    echo.
)

pause
goto menu

:monthly
cls
echo ================================================
echo             设置月度数据获取任务
echo ================================================
echo.
echo 请输入每月执行的日期（1-31）：
echo 注意：如果某月没有指定日期，任务将在该月的最后一天执行
echo.

set /p MONTH_DAY=请输入日期: 

:: 验证日期格式
echo %MONTH_DAY% | findstr /r /c:"^[1-9]$" /c:"^[1-2][0-9]$" /c:"^3[0-1]$" > nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 日期格式无效，请输入 1-31 之间的数字。
    echo.
    pause
    goto monthly
)

:set_monthly_time
cls
echo ================================================
echo             设置执行时间
echo ================================================
echo.
echo 请输入执行时间（24小时制，格式：HH:MM）：
echo 例如：09:00 表示上午9点整
echo.

set /p EXEC_TIME=请输入执行时间: 

:: 验证时间格式
echo %EXEC_TIME% | findstr /r /c:"^[0-2][0-9]:[0-5][0-9]$" > nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 时间格式无效，请使用 HH:MM 格式（24小时制）。
    echo.
    pause
    goto set_monthly_time
)

:: 提取小时和分钟
for /f "tokens=1,2 delims=:" %%a in ("%EXEC_TIME%") do (
    set "HOUR=%%a"
    set "MINUTE=%%b"
)

:: 验证小时是否有效
if %HOUR% GTR 23 (
    echo.
    echo 小时必须在 0-23 之间。
    echo.
    pause
    goto set_monthly_time
)

:: 创建计划任务
set "TASK_NAME=%TASK_PREFIX%Monthly"
set "TASK_DESC=每月%MONTH_DAY%日执行月度数据获取任务"

cls
echo ================================================
echo             创建计划任务
echo ================================================
echo.
echo 任务名称: %TASK_NAME%
echo 任务描述: %TASK_DESC%
echo 执行日期: 每月%MONTH_DAY%日
echo 执行时间: %EXEC_TIME%
echo.

schtasks /create /tn "%TASK_NAME%" /tr "\"%DATA_FETCHER_DIR%\monthly_data_fetcher.bat\"" /sc MONTHLY /mo 1 /d %MONTH_DAY% /st %EXEC_TIME% /f /rl HIGHEST /ru "SYSTEM" /np

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 创建计划任务失败，请检查是否有管理员权限。
    echo.
) else (
    echo.
    echo 计划任务创建成功！
    echo.
)

pause
goto menu

:quarterly
cls
echo ================================================
echo             设置季度数据获取任务
echo ================================================
echo.
echo 季度任务将在每季度初（1月、4月、7月、10月）的指定日期执行
echo.
echo 请输入每季度初执行的日期（1-31）：
echo 建议设置为 1-5 之间的数字，确保每个季度初都能执行
echo.

set /p QUARTER_DAY=请输入日期: 

:: 验证日期格式
echo %QUARTER_DAY% | findstr /r /c:"^[1-9]$" /c:"^[1-2][0-9]$" /c:"^3[0-1]$" > nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 日期格式无效，请输入 1-31 之间的数字。
    echo.
    pause
    goto quarterly
)

:set_quarterly_time
cls
echo ================================================
echo             设置执行时间
echo ================================================
echo.
echo 请输入执行时间（24小时制，格式：HH:MM）：
echo 例如：10:30 表示上午10点30分
echo.

set /p EXEC_TIME=请输入执行时间: 

:: 验证时间格式
echo %EXEC_TIME% | findstr /r /c:"^[0-2][0-9]:[0-5][0-9]$" > nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 时间格式无效，请使用 HH:MM 格式（24小时制）。
    echo.
    pause
    goto set_quarterly_time
)

:: 提取小时和分钟
for /f "tokens=1,2 delims=:" %%a in ("%EXEC_TIME%") do (
    set "HOUR=%%a"
    set "MINUTE=%%b"
)

:: 验证小时是否有效
if %HOUR% GTR 23 (
    echo.
    echo 小时必须在 0-23 之间。
    echo.
    pause
    goto set_quarterly_time
)

:: 创建四个季度的计划任务
set "TASK_NAME_Q1=%TASK_PREFIX%Quarterly_Q1"
set "TASK_DESC_Q1=第一季度（1月%QUARTER_DAY%日）执行季度数据获取任务"

set "TASK_NAME_Q2=%TASK_PREFIX%Quarterly_Q2"
set "TASK_DESC_Q2=第二季度（4月%QUARTER_DAY%日）执行季度数据获取任务"

set "TASK_NAME_Q3=%TASK_PREFIX%Quarterly_Q3"
set "TASK_DESC_Q3=第三季度（7月%QUARTER_DAY%日）执行季度数据获取任务"

set "TASK_NAME_Q4=%TASK_PREFIX%Quarterly_Q4"
set "TASK_DESC_Q4=第四季度（10月%QUARTER_DAY%日）执行季度数据获取任务"

cls
echo ================================================
echo             创建季度计划任务
echo ================================================
echo.
echo 正在创建第一季度计划任务...
schtasks /create /tn "%TASK_NAME_Q1%" /tr "\"%DATA_FETCHER_DIR%\quarterly_data_fetcher.bat\"" /sc MONTHLY /mo 12 /d %QUARTER_DAY% /st %EXEC_TIME% /f /rl HIGHEST /ru "SYSTEM" /np /m "JAN"

echo 正在创建第二季度计划任务...
schtasks /create /tn "%TASK_NAME_Q2%" /tr "\"%DATA_FETCHER_DIR%\quarterly_data_fetcher.bat\"" /sc MONTHLY /mo 12 /d %QUARTER_DAY% /st %EXEC_TIME% /f /rl HIGHEST /ru "SYSTEM" /np /m "APR"

echo 正在创建第三季度计划任务...
schtasks /create /tn "%TASK_NAME_Q3%" /tr "\"%DATA_FETCHER_DIR%\quarterly_data_fetcher.bat\"" /sc MONTHLY /mo 12 /d %QUARTER_DAY% /st %EXEC_TIME% /f /rl HIGHEST /ru "SYSTEM" /np /m "JUL"

echo 正在创建第四季度计划任务...
schtasks /create /tn "%TASK_NAME_Q4%" /tr "\"%DATA_FETCHER_DIR%\quarterly_data_fetcher.bat\"" /sc MONTHLY /mo 12 /d %QUARTER_DAY% /st %EXEC_TIME% /f /rl HIGHEST /ru "SYSTEM" /np /m "OCT"

echo.
echo 季度计划任务创建完成！
echo.

pause
goto menu

:view
cls
echo ================================================
echo             查看已设置的计划任务
echo ================================================
echo.
echo 正在查询计划任务...
echo.

schtasks /query /fo list /v | findstr /i "%TASK_PREFIX%"

echo.
echo 提示：如需查看详细信息，请在命令提示符中运行：
echo       schtasks /query /tn "任务名称" /fo list /v
echo.

pause
goto menu

:delete
cls
echo ================================================
echo             删除计划任务
echo ================================================
echo.
echo 已设置的计划任务：
echo.

schtasks /query /fo list | findstr /i "%TASK_PREFIX%"

echo.
echo 请输入要删除的任务名称（完整名称）：
echo 例如：%TASK_PREFIX%Daily_Everyday
echo 输入 ALL 删除所有 %TASK_PREFIX% 开头的任务
echo 输入 BACK 返回上级菜单
echo.

set /p DEL_TASK=请输入任务名称: 

if /i "%DEL_TASK%"=="BACK" goto menu

if /i "%DEL_TASK%"=="ALL" (
    echo.
    echo 确定要删除所有 %TASK_PREFIX% 开头的计划任务吗？
    echo 此操作不可恢复！(Y/N)
    echo.
    
    set /p CONFIRM=请确认: 
    
    if /i "%CONFIRM%"=="Y" (
        for /f "tokens=*" %%a in ('schtasks /query /fo list ^| findstr /i "%TASK_PREFIX%"') do (
            for /f "tokens=2 delims=:" %%b in ("%%a") do (
                set "TASK_TO_DEL=%%b"
                set "TASK_TO_DEL=!TASK_TO_DEL:~1!"
                schtasks /delete /tn "!TASK_TO_DEL!" /f
            )
        )
        echo.
        echo 所有 %TASK_PREFIX% 开头的计划任务已删除。
        echo.
    ) else (
        echo.
        echo 操作已取消。
        echo.
    )
) else (
    schtasks /delete /tn "%DEL_TASK%" /f
    
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo 删除计划任务失败，请检查任务名称是否正确。
        echo.
    ) else (
        echo.
        echo 计划任务 %DEL_TASK% 已成功删除。
        echo.
    )
)

pause
goto menu

:end
cls
echo ================================================
echo             计划任务调度器已退出
echo ================================================
echo.
exit /b 0