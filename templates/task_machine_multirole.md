# Task Machine Template — Multi-Role Project Brief

*Note: This template demonstrates two approaches for role definitions: (1) Reference existing agents from the `.github/agents` folder when suitable ones are available, and (2) Define custom roles inline when no predefined agent matches the project needs. The planner will automatically discover available agents and choose the best approach for each role.*

## Role Descriptions

### Role: data-analyst
- Agent Path: `.github/agents/05-data-ai/data-analyst.md`

### Role: Custom Marketing Specialist
- Purpose: Create targeted marketing campaigns and analyze customer engagement metrics
- Focus: Brand positioning, customer segmentation, conversion optimization, and multi-channel campaign management
- Style: Creative yet analytical, customer-focused, results-driven
- Note: Custom role defined inline (no matching predefined agent available)

### Role: backend-developer
- Agent Path: `.github/agents/01-core-development/backend-developer.md`

## Tasks

- [ ] [data-analyst] Analyze the raw data sources and create a structured summary with key findings saved to `${OUTPUT_DIR}/data_summary.md`.
- [ ] [data-analyst] Read the data summary from `${OUTPUT_DIR}/data_summary.md` and extract the top 3 actionable insights.
- [ ] [Custom Marketing Specialist] Review the insights and create targeted marketing recommendations, saving them to `${OUTPUT_DIR}/marketing_strategy.md`.
- [ ] [backend-developer] Evaluate technical requirements and create an implementation plan saved to `${OUTPUT_DIR}/tech_plan.txt`.
- [ ] [backend-developer] Read the implementation plan from `${OUTPUT_DIR}/tech_plan.txt` and provide final recommendations.
