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
set "ROOT_DIR=%~dp0..\..\"
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
echo  [2] 设置周度数据获取任务
echo  [3] 设置月度数据获取任务
echo  [4] 设置季度数据获取任务
echo  [5] 查看已设置的计划任务
echo  [6] 删除计划任务
echo  [0] 返回主菜单
echo.
echo ================================================
echo.

set /p choice="请输入选项 [0-6]: "

if "%choice%"=="1" goto daily
if "%choice%"=="2" goto weekly
if "%choice%"=="3" goto monthly
if "%choice%"=="4" goto quarterly
if "%choice%"=="5" goto view
if "%choice%"=="6" goto delete
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
echo 请选择执行频率:
echo [1] 每天执行
echo [2] 工作日执行
echo [3] 自定义执行时间
echo [0] 返回上级菜单
echo.
echo ================================================
echo.

set /p daily_choice="请输入选项 [0-3]: "

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
set "SCHEDULE_TYPE=DAILY"
set "TASK_NAME=%TASK_PREFIX%Daily_Data_Fetcher"
set "TASK_DESC=每天执行日度数据获取任务"
goto set_daily_time

:daily_workday
set "SCHEDULE_TYPE=WEEKLY"
set "DAYS=MON,TUE,WED,THU,FRI"
set "TASK_NAME=%TASK_PREFIX%Daily_Data_Fetcher_Workdays"
set "TASK_DESC=工作日执行日度数据获取任务"
goto set_daily_time

:daily_custom
cls
echo ================================================
echo             设置自定义日期执行
echo ================================================
echo.
echo 请选择执行日期(多选请用逗号分隔，如:MON,WED,FRI):
echo MON=周一, TUE=周二, WED=周三, THU=周四
echo FRI=周五, SAT=周六, SUN=周日
echo 或输入具体日期: 1-31
echo.
echo 示例: MON,WED,FRI 或 1,15
echo.

set /p custom_days="请输入执行日期: "

set "SCHEDULE_TYPE=WEEKLY"
set "DAYS=%custom_days%"
set "TASK_NAME=%TASK_PREFIX%Daily_Data_Fetcher_Custom"
set "TASK_DESC=自定义日期执行日度数据获取任务"
goto set_daily_time

:set_daily_time
cls
echo ================================================
echo             设置执行时间
echo ================================================
echo.
echo 请输入执行时间(24小时制，格式:HH:MM):
echo 例如:16:30 表示下午4点30分
echo.

set /p EXEC_TIME="请输入执行时间: "

:: 验证时间格式
echo %EXEC_TIME% | findstr /r "^[0-2][0-9]:[0-5][0-9]$" > nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 时间格式无效，请使用 HH:MM 格式(24小时制)。
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

:: 设置任务命令和时间
set "TASK_TIME=%EXEC_TIME%"
set "TASK_CMD=%DATA_FETCHER_DIR%\daily_data_fetcher.bat"
goto create_task

:weekly
cls
echo ================================================
echo             设置周度数据获取任务
echo ================================================
echo.
echo 请选择执行频率:
echo [1] 每周一执行
echo [2] 每周五执行
echo [3] 自定义周几执行
echo [0] 返回上级菜单
echo.
echo ================================================
echo.

set /p weekly_choice="请输入选项 [0-3]: "

if "%weekly_choice%"=="1" goto weekly_monday
if "%weekly_choice%"=="2" goto weekly_friday
if "%weekly_choice%"=="3" goto weekly_custom
if "%weekly_choice%"=="0" goto menu

echo.
echo 无效的选项，请重新输入。
echo.
pause
goto weekly

:weekly_monday
set "SCHEDULE_TYPE=WEEKLY"
set "DAYS=MON"
set "TASK_NAME=%TASK_PREFIX%Weekly_Data_Fetcher_Monday"
set "TASK_DESC=每周一执行周度数据获取任务"
goto set_weekly_time

:weekly_friday
set "SCHEDULE_TYPE=WEEKLY"
set "DAYS=FRI"
set "TASK_NAME=%TASK_PREFIX%Weekly_Data_Fetcher_Friday"
set "TASK_DESC=每周五执行周度数据获取任务"
goto set_weekly_time

:weekly_custom
cls
echo ================================================
echo             设置自定义周几执行
echo ================================================
echo.
echo 请选择执行的星期几:
echo [1] 周一 [2] 周二 [3] 周三 [4] 周四
echo [5] 周五 [6] 周六 [7] 周日
echo.

set /p custom_day="请输入选项 [1-7]: "

if "%custom_day%"=="1" set "DAYS=MON"
if "%custom_day%"=="2" set "DAYS=TUE"
if "%custom_day%"=="3" set "DAYS=WED"
if "%custom_day%"=="4" set "DAYS=THU"
if "%custom_day%"=="5" set "DAYS=FRI"
if "%custom_day%"=="6" set "DAYS=SAT"
if "%custom_day%"=="7" set "DAYS=SUN"

if "%DAYS%"=="" (
    echo.
    echo 无效的选项，请重新输入。
    echo.
    pause
    goto weekly_custom
)

set "SCHEDULE_TYPE=WEEKLY"
set "TASK_NAME=%TASK_PREFIX%Weekly_Data_Fetcher_Custom"
set "TASK_DESC=自定义周几执行周度数据获取任务"
goto set_weekly_time

:set_weekly_time
cls
echo ================================================
echo             设置周度任务执行时间
echo ================================================
echo.
echo 请输入执行时间(24小时制，例如:14:30):
echo.

set /p exec_time="请输入执行时间: "

set "TASK_TIME=%exec_time%"
set "TASK_CMD=%DATA_FETCHER_DIR%\weekly_data_fetcher.bat"
goto create_task

:monthly
cls
echo ================================================
echo             设置月度数据获取任务
echo ================================================
echo.
echo 请输入每月执行的日期（1-31）：
echo 注意：如果某月没有指定日期，任务将在该月的最后一天执行
echo.

set /p MONTH_DAY="请输入日期: "

if "%MONTH_DAY%"=="0" goto menu

:: 验证日期格式
echo %MONTH_DAY% | findstr /r "^[1-9][0-9]*$" > nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 日期格式无效，请输入 1-31 之间的数字。
    echo.
    pause
    goto monthly
)

if %MONTH_DAY% GTR 31 (
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
echo.

set /p EXEC_TIME="请输入执行时间: "

:: 验证时间格式
echo %EXEC_TIME% | findstr /r "^[0-2][0-9]:[0-5][0-9]$" > nul
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

set "SCHEDULE_TYPE=MONTHLY"
set "TASK_NAME=%TASK_PREFIX%Monthly_Data_Fetcher"
set "TASK_DESC=每月%MONTH_DAY%日执行月度数据获取任务"
set "TASK_TIME=%EXEC_TIME%"
set "TASK_CMD=%DATA_FETCHER_DIR%\monthly_data_fetcher.bat"
goto create_task

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

set /p QUARTER_DAY="请输入日期: "

if "%QUARTER_DAY%"=="0" goto menu

:: 验证日期格式
echo %QUARTER_DAY% | findstr /r "^[1-9][0-9]*$" > nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 日期格式无效，请输入 1-31 之间的数字。
    echo.
    pause
    goto quarterly
)

if %QUARTER_DAY% GTR 31 (
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
echo.

set /p EXEC_TIME="请输入执行时间: "

:: 验证时间格式
echo %EXEC_TIME% | findstr /r "^[0-2][0-9]:[0-5][0-9]$" > nul
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

:: 设置任务命令和时间
set "SCHEDULE_TYPE=MONTHLY"
set "TASK_TIME=%EXEC_TIME%"
set "TASK_CMD=%DATA_FETCHER_DIR%\quarterly_data_fetcher.bat"

set "TASK_DESC_Q1=第一季度（1月%QUARTER_DAY%日）执行季度数据获取任务"
set "TASK_NAME_Q1=%TASK_PREFIX%Quarterly_Q1_Data_Fetcher"
set "TASK_DESC_Q2=第二季度（4月%QUARTER_DAY%日）执行季度数据获取任务"
set "TASK_NAME_Q2=%TASK_PREFIX%Quarterly_Q2_Data_Fetcher"
set "TASK_DESC_Q3=第三季度（7月%QUARTER_DAY%日）执行季度数据获取任务"
set "TASK_NAME_Q3=%TASK_PREFIX%Quarterly_Q3_Data_Fetcher"
set "TASK_DESC_Q4=第四季度（10月%QUARTER_DAY%日）执行季度数据获取任务"
set "TASK_NAME_Q4=%TASK_PREFIX%Quarterly_Q4_Data_Fetcher"

:: 创建四个季度任务
echo 正在创建季度任务...
echo.

schtasks /create /tn "%TASK_NAME_Q1%" /tr "\"%TASK_CMD%\"" /sc MONTHLY /st %TASK_TIME% /f /rl HIGHEST /ru "SYSTEM" /m JAN /d %QUARTER_DAY% /np
schtasks /create /tn "%TASK_NAME_Q2%" /tr "\"%TASK_CMD%\"" /sc MONTHLY /st %TASK_TIME% /f /rl HIGHEST /ru "SYSTEM" /m APR /d %QUARTER_DAY% /np
schtasks /create /tn "%TASK_NAME_Q3%" /tr "\"%TASK_CMD%\"" /sc MONTHLY /st %TASK_TIME% /f /rl HIGHEST /ru "SYSTEM" /m JUL /d %QUARTER_DAY% /np
schtasks /create /tn "%TASK_NAME_Q4%" /tr "\"%TASK_CMD%\"" /sc MONTHLY /st %TASK_TIME% /f /rl HIGHEST /ru "SYSTEM" /m OCT /d %QUARTER_DAY% /np

echo.
echo 季度任务创建完成！
echo.
pause
goto menu

:view
cls
echo ================================================
echo             查看已设置的计划任务
echo ================================================
echo.
schtasks /query /fo table | findstr "StockA_"
echo.
echo ================================================
echo.
pause
goto menu

:delete
cls
echo ================================================
echo             删除计划任务
echo ================================================
echo.
echo 当前已设置的股票数据任务:
schtasks /query /fo table | findstr "StockA_"
echo.
echo ================================================
echo.

set /p DEL_TASK="请输入任务名称: "

if /i "%DEL_TASK%"=="BACK" goto menu

if "%DEL_TASK%"=="" (
    echo.
    echo 任务名称不能为空。
    echo.
    pause
    goto delete
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

:create_task
:: 创建计划任务
cls
echo ================================================
echo             创建计划任务
echo ================================================
echo.
echo 任务名称: %TASK_NAME%
echo 任务描述: %TASK_DESC%
echo 执行时间: %TASK_TIME%
echo.

if "%SCHEDULE_TYPE%"=="DAILY" (
    schtasks /create /tn "%TASK_NAME%" /tr "\"%TASK_CMD%\"" /sc DAILY /st %TASK_TIME% /f /rl HIGHEST /ru "SYSTEM" /np
) else if "%SCHEDULE_TYPE%"=="WEEKLY" (
    schtasks /create /tn "%TASK_NAME%" /tr "\"%TASK_CMD%\"" /sc WEEKLY /st %TASK_TIME% /f /rl HIGHEST /ru "SYSTEM" /d %DAYS% /np
) else if "%SCHEDULE_TYPE%"=="MONTHLY" (
    schtasks /create /tn "%TASK_NAME%" /tr "\"%TASK_CMD%\"" /sc MONTHLY /st %TASK_TIME% /f /rl HIGHEST /ru "SYSTEM" /d %MONTH_DAY% /np
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 计划任务创建成功！
    echo.
) else (
    echo.
    echo 计划任务创建失败，请检查权限或参数设置。
    echo.
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
