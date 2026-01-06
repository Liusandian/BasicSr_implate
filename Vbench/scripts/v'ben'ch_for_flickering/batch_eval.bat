@echo off
REM 批量评测脚本 (Windows版本)
REM 用于自动评测多个场景和相机

setlocal enabledelayedexpansion

REM 配置
set VIDEO_BASE_DIR=test_videos
set RESULTS_BASE_DIR=results
set REPORTS_DIR=reports
set EVAL_MODE=standard

REM 创建输出目录
if not exist "%RESULTS_BASE_DIR%" mkdir "%RESULTS_BASE_DIR%"
if not exist "%REPORTS_DIR%" mkdir "%REPORTS_DIR%"

echo ================================================
echo    纹理抖动批量评测工具 (Windows)
echo ================================================
echo.

REM 检查Python
echo 检查环境...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [错误] Python未安装或未添加到PATH
    pause
    exit /b 1
)

python -c "import torch" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [错误] PyTorch未安装
    pause
    exit /b 1
)

echo [OK] 环境检查通过
echo.

REM 场景列表
set SCENES=grass night glass motion

set SUCCESS_COUNT=0
set FAIL_COUNT=0

echo 开始批量评测...
echo   评测模式: %EVAL_MODE%
echo.

for %%s in (%SCENES%) do (
    echo.
    echo ================================================
    echo 评测场景: %%s
    echo ================================================
    
    set video_dir=%VIDEO_BASE_DIR%\%%s
    set results_dir=%RESULTS_BASE_DIR%\%%s
    set report_file=%REPORTS_DIR%\%%s_report.md
    
    REM 检查视频目录
    if not exist "!video_dir!" (
        echo [警告] 跳过: 目录不存在 - !video_dir!
        continue
    )
    
    REM 检查视频文件
    dir /b "!video_dir!\*.mp4" 2>nul | findstr "." >nul
    if %ERRORLEVEL% neq 0 (
        echo [警告] 跳过: 未找到视频文件
        continue
    )
    
    echo   视频目录: !video_dir!
    echo   结果目录: !results_dir!
    echo.
    
    REM 执行评测
    echo [开始] 评测中...
    
    python "scripts\v'ben'ch_for_flickering\texture_jitter_eval.py" ^
        --video_dir "!video_dir!" ^
        --mode "%EVAL_MODE%" ^
        --output_dir "!results_dir!"
    
    if %ERRORLEVEL% equ 0 (
        echo [OK] 评测完成
        
        REM 生成报告
        echo [开始] 生成报告...
        
        python "scripts\v'ben'ch_for_flickering\analyze_results.py" ^
            --results_dir "!results_dir!" ^
            --output "!report_file!"
        
        if %ERRORLEVEL% equ 0 (
            echo [OK] 报告已生成: !report_file!
            set /a SUCCESS_COUNT+=1
        ) else (
            echo [失败] 报告生成失败
            set /a FAIL_COUNT+=1
        )
    ) else (
        echo [失败] 评测失败
        set /a FAIL_COUNT+=1
    )
)

REM 汇总结果
echo.
echo ================================================
echo 批量评测完成
echo ================================================
echo   成功: %SUCCESS_COUNT% 个场景
echo   失败: %FAIL_COUNT% 个场景
echo.
echo 结果文件位置:
echo   - 评测结果: %RESULTS_BASE_DIR%\
echo   - 评测报告: %REPORTS_DIR%\
echo.

REM 生成汇总报告
if %SUCCESS_COUNT% gtr 0 (
    echo [开始] 生成汇总报告...
    
    set SUMMARY_FILE=%REPORTS_DIR%\summary.md
    
    (
        echo # 纹理抖动评测汇总报告
        echo.
        echo **生成时间:** %DATE% %TIME%
        echo **评测模式:** %EVAL_MODE%
        echo.
        echo ---
        echo.
        echo ## 评测场景
        echo.
        
        for %%s in (%SCENES%) do (
            if exist "%REPORTS_DIR%\%%s_report.md" (
                echo - [%%s场景报告](%%s_report.md^)
            )
        )
        
        echo.
        echo ---
        echo.
        echo 详细结果请查看各场景的独立报告。
        
    ) > "!SUMMARY_FILE!"
    
    echo [OK] 汇总报告已生成: !SUMMARY_FILE!
)

echo.
echo [完成] 所有任务完成！
echo.
pause

