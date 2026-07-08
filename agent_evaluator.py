"""
Agent-based CLI Tool Evaluation System
Uses AI agents to deeply analyze CLI tools for quality and agent compatibility
"""

import json
from typing import Dict, List, Any


class AgentEvaluator:
    """
    Evaluates CLI tools using multi-dimensional agent analysis

    Each agent specializes in different evaluation dimensions:
    - Agent Compatibility Agent: JSON output, structured commands, documentation
    - Quality Assessment Agent: Code quality, test coverage, maintenance status
    - Trending Analysis Agent: Community feedback, adoption velocity
    - Use Case Discovery Agent: Real-world applications and integrations
    """

    EVALUATION_SCHEMA = {
        "type": "object",
        "properties": {
            "agent_compatibility": {
                "type": "object",
                "properties": {
                    "json_output_support": {"type": "number", "minimum": 0, "maximum": 100},
                    "command_structure": {"type": "number", "minimum": 0, "maximum": 100},
                    "documentation_quality": {"type": "number", "minimum": 0, "maximum": 100},
                    "error_handling": {"type": "number", "minimum": 0, "maximum": 100},
                    "overall_agent_score": {"type": "number", "minimum": 0, "maximum": 100}
                }
            },
            "quality_metrics": {
                "type": "object",
                "properties": {
                    "code_maturity": {"type": "number", "minimum": 0, "maximum": 100},
                    "test_coverage": {"type": "number", "minimum": 0, "maximum": 100},
                    "maintenance_activity": {"type": "number", "minimum": 0, "maximum": 100},
                    "security_posture": {"type": "number", "minimum": 0, "maximum": 100},
                    "overall_quality_score": {"type": "number", "minimum": 0, "maximum": 100}
                }
            },
            "trending_indicators": {
                "type": "object",
                "properties": {
                    "github_momentum": {"type": "number", "minimum": 0, "maximum": 100},
                    "community_engagement": {"type": "number", "minimum": 0, "maximum": 100},
                    "adoption_trajectory": {"type": "number", "minimum": 0, "maximum": 100},
                    "overall_trending_score": {"type": "number", "minimum": 0, "maximum": 100}
                }
            },
            "use_cases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "description": {"type": "string"},
                        "agent_compatibility_level": {"type": "string", "enum": ["low", "medium", "high"]}
                    }
                }
            },
            "summary": {
                "type": "object",
                "properties": {
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "weaknesses": {"type": "array", "items": {"type": "string"}},
                    "recommendation": {"type": "string"}
                }
            }
        }
    }

    @staticmethod
    def get_agent_prompts() -> Dict[str, str]:
        """Return prompts for different evaluation agents"""
        return {
            "agent_compatibility": """
Evaluate this CLI tool specifically for AI agent compatibility.
Consider:
1. Does it support JSON output for structured machine consumption?
2. Are commands and flags well-structured and predictable?
3. Is help documentation comprehensive and machine-parseable?
4. How are errors reported and handled?
5. Would an LLM agent find this tool easy to invoke and integrate?

Provide scores for each dimension (0-100) and an overall agent compatibility score.
""",
            "quality_metrics": """
Assess the overall quality and production-readiness of this CLI tool.
Consider:
1. Code maturity (version number, stability, API freeze)
2. Test coverage and test quality
3. Activity level and maintenance patterns
4. Security vulnerabilities and fixes
5. Documentation completeness and examples

Provide scores for each dimension (0-100) and an overall quality score.
""",
            "trending_indicators": """
Analyze the trending and adoption signals for this CLI tool.
Consider:
1. GitHub stars/forks growth rate
2. Issue response time and community engagement
3. Adoption trajectory (is it growing or stagnating?)
4. Media mentions and industry adoption
5. Integration ecosystem growth

Provide scores for each dimension (0-100) and an overall trending score.
""",
            "use_cases": """
Identify practical use cases and applications for this CLI tool, especially for AI agents.
For each use case:
1. Describe the category and what it enables
2. Explain how an AI agent could leverage it
3. Rate the agent compatibility level (low/medium/high)

Include 3-5 most compelling use cases.
List both strengths and weaknesses of this tool.
Provide a recommendation for AI agent developers.
"""
        }

    def create_evaluation_prompt(self, tool_name: str, tool_description: str, dimension: str) -> str:
        """Create evaluation prompt for a specific tool and dimension"""
        base_prompt = self.get_agent_prompts()[dimension]
        return f"""
Evaluate the CLI tool: {tool_name}
Description: {tool_description}

{base_prompt}

Return your evaluation in the specified JSON format for this dimension.
"""

    def aggregate_evaluations(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate evaluations from multiple agents into a comprehensive score"""
        if not evaluations:
            return {}

        # Extract component scores
        agent_scores = [e.get("agent_compatibility", {}).get("overall_agent_score", 0) for e in evaluations]
        quality_scores = [e.get("quality_metrics", {}).get("overall_quality_score", 0) for e in evaluations]
        trending_scores = [e.get("trending_indicators", {}).get("overall_trending_score", 0) for e in evaluations]

        # Calculate averages and weights
        avg_agent = sum(agent_scores) / len(agent_scores) if agent_scores else 0
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_trending = sum(trending_scores) / len(trending_scores) if trending_scores else 0

        # Weighted overall score (for AI tools, agent compatibility is most important)
        overall_score = (avg_agent * 0.5 + avg_quality * 0.35 + avg_trending * 0.15)

        return {
            "agent_compatibility_score": avg_agent,
            "quality_score": avg_quality,
            "trending_score": avg_trending,
            "overall_evaluation_score": overall_score,
            "recommendation": "RECOMMENDED" if overall_score > 70 else "CONSIDER" if overall_score > 50 else "WATCH"
        }


def create_workflow_script() -> str:
    """Create a Workflow script for parallel agent evaluation"""
    return """
export const meta = {
  name: 'cli-tools-evaluation',
  description: 'Multi-agent evaluation of CLI tools for quality and agent compatibility',
  phases: [
    { title: 'Analyze', detail: 'Evaluate CLI tools across multiple dimensions' },
    { title: 'Aggregate', detail: 'Combine evaluations into comprehensive scores' }
  ]
}

const TOOLS_TO_EVALUATE = [
  { name: 'Blender CLI', description: '3D modeling, animation and rendering from command line' },
  { name: 'LibreOffice CLI', description: 'Document processing, spreadsheets, presentations via CLI' },
  { name: 'GIMP CLI', description: 'Image editing and manipulation from terminal' },
  { name: 'Ollama CLI', description: 'Run large language models locally' },
  { name: 'ComfyUI CLI', description: 'Diffusion model UI and workflows via CLI' }
]

const DIMENSIONS = [
  'agent_compatibility',
  'quality_metrics',
  'trending_indicators',
  'use_cases'
]

phase('Analyze')

const evaluations = await pipeline(
  TOOLS_TO_EVALUATE,
  async (tool) => {
    return await parallel(
      DIMENSIONS.map(dim => () =>
        agent(
          `Evaluate "${tool.name}" for ${dim.replace(/_/g, ' ')}:\\n${tool.description}`,
          {
            label: `${tool.name}:${dim}`,
            phase: 'Analyze'
          }
        )
      )
    )
  },
  (dimensionResults, tool) => ({
    tool: tool.name,
    evaluations: dimensionResults.filter(Boolean)
  })
)

phase('Aggregate')

const aggregated = evaluations
  .filter(Boolean)
  .map(result => ({
    tool: result.tool,
    analysis: result.evaluations
  }))

return {
  total_tools: TOOLS_TO_EVALUATE.length,
  evaluated_tools: aggregated.length,
  evaluations: aggregated
}
"""


if __name__ == "__main__":
    evaluator = AgentEvaluator()

    # Example: Create prompt for Ollama CLI evaluation
    prompt = evaluator.create_evaluation_prompt(
        "Ollama CLI",
        "Run large language models locally",
        "agent_compatibility"
    )
    print(prompt)

    # Example aggregation
    sample_evaluations = [
        {
            "agent_compatibility": {"overall_agent_score": 85},
            "quality_metrics": {"overall_quality_score": 80},
            "trending_indicators": {"overall_trending_score": 90}
        }
    ]
    result = evaluator.aggregate_evaluations(sample_evaluations)
    print("\nAggregated Evaluation:")
    print(json.dumps(result, indent=2))
