#!/bin/bash
# 批量评测脚本
# 用于自动评测多个场景和相机

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
VIDEO_BASE_DIR="test_videos"
RESULTS_BASE_DIR="results"
REPORTS_DIR="reports"
EVAL_MODE="standard"  # fast, standard, professional

# 创建输出目录
mkdir -p "$RESULTS_BASE_DIR"
mkdir -p "$REPORTS_DIR"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   纹理抖动批量评测工具${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 检查Python和依赖
echo -e "${YELLOW}检查环境...${NC}"
if ! command -v python &> /dev/null; then
    echo -e "${RED}错误: Python未安装${NC}"
    exit 1
fi

if ! python -c "import torch" &> /dev/null; then
    echo -e "${RED}错误: PyTorch未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 环境检查通过${NC}"
echo ""

# 场景列表
SCENES=("grass" "night" "glass" "motion")

# 主评测流程
echo -e "${BLUE}开始批量评测...${NC}"
echo -e "  评测模式: ${EVAL_MODE}"
echo -e "  场景数量: ${#SCENES[@]}"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for scene in "${SCENES[@]}"; do
    echo ""
    echo -e "${YELLOW}================================================${NC}"
    echo -e "${YELLOW}评测场景: ${scene}${NC}"
    echo -e "${YELLOW}================================================${NC}"
    
    video_dir="${VIDEO_BASE_DIR}/${scene}"
    results_dir="${RESULTS_BASE_DIR}/${scene}"
    report_file="${REPORTS_DIR}/${scene}_report.md"
    
    # 检查视频目录是否存在
    if [ ! -d "$video_dir" ]; then
        echo -e "${YELLOW}⚠️  跳过: 目录不存在 - ${video_dir}${NC}"
        continue
    fi
    
    # 检查是否有视频文件
    video_count=$(find "$video_dir" -type f \( -iname "*.mp4" -o -iname "*.avi" -o -iname "*.mov" \) | wc -l)
    if [ "$video_count" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  跳过: 未找到视频文件${NC}"
        continue
    fi
    
    echo -e "  视频目录: ${video_dir}"
    echo -e "  视频数量: ${video_count}"
    echo -e "  结果目录: ${results_dir}"
    echo ""
    
    # 执行评测
    echo -e "${GREEN}开始评测...${NC}"
    
    if python scripts/v\'ben\'ch_for_flickering/texture_jitter_eval.py \
        --video_dir "$video_dir" \
        --mode "$EVAL_MODE" \
        --output_dir "$results_dir"; then
        
        echo -e "${GREEN}✓ 评测完成${NC}"
        
        # 生成报告
        echo -e "${GREEN}生成报告...${NC}"
        
        if python scripts/v\'ben\'ch_for_flickering/analyze_results.py \
            --results_dir "$results_dir" \
            --output "$report_file"; then
            
            echo -e "${GREEN}✓ 报告已生成: ${report_file}${NC}"
            ((SUCCESS_COUNT++))
        else
            echo -e "${RED}✗ 报告生成失败${NC}"
            ((FAIL_COUNT++))
        fi
    else
        echo -e "${RED}✗ 评测失败${NC}"
        ((FAIL_COUNT++))
    fi
done

# 汇总结果
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}批量评测完成${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "  成功: ${GREEN}${SUCCESS_COUNT}${NC} 个场景"
echo -e "  失败: ${RED}${FAIL_COUNT}${NC} 个场景"
echo ""
echo -e "结果文件位置:"
echo -e "  - 评测结果: ${RESULTS_BASE_DIR}/"
echo -e "  - 评测报告: ${REPORTS_DIR}/"
echo ""

# 生成汇总报告
if [ "$SUCCESS_COUNT" -gt 0 ]; then
    echo -e "${GREEN}生成汇总报告...${NC}"
    
    SUMMARY_FILE="${REPORTS_DIR}/summary.md"
    
    {
        echo "# 纹理抖动评测汇总报告"
        echo ""
        echo "**生成时间:** $(date '+%Y-%m-%d %H:%M:%S')"
        echo "**评测模式:** ${EVAL_MODE}"
        echo ""
        echo "---"
        echo ""
        echo "## 评测场景"
        echo ""
        
        for scene in "${SCENES[@]}"; do
            report_file="${REPORTS_DIR}/${scene}_report.md"
            if [ -f "$report_file" ]; then
                echo "- [${scene}场景报告](${scene}_report.md)"
            fi
        done
        
        echo ""
        echo "---"
        echo ""
        echo "## 快速查看"
        echo ""
        
        for scene in "${SCENES[@]}"; do
            report_file="${REPORTS_DIR}/${scene}_report.md"
            if [ -f "$report_file" ]; then
                echo "### ${scene} 场景"
                echo ""
                echo "\`\`\`"
                head -n 30 "$report_file" | tail -n 20
                echo "\`\`\`"
                echo ""
            fi
        done
        
    } > "$SUMMARY_FILE"
    
    echo -e "${GREEN}✓ 汇总报告已生成: ${SUMMARY_FILE}${NC}"
fi

echo -e "${BLUE}所有任务完成！${NC}"

