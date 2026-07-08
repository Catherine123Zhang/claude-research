"""
Report generation for Daily CLI Trending Tools
Supports JSON, Markdown, and HTML formats
"""

from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Any
import json


class ReportGenerator:
    """Generates reports in multiple formats"""

    @staticmethod
    def generate_markdown(report: Any) -> str:
        """Generate Markdown format report"""
        md = []
        md.append(f"# 🚀 Daily CLI Trending Tools Report")
        md.append(f"\n**Date:** {report.date}")
        md.append(f"**Total Tools Analyzed:** {report.total_tools}")
        md.append(f"**Average Quality Score:** {report.trending_score_avg:.1f}/100\n")

        # Top tools section
        md.append("## 🏆 Top 5 Trending Tools\n")
        for i, tool in enumerate(report.top_tools, 1):
            md.append(f"### {i}. {tool.name}")
            md.append(f"- **Category:** {tool.category}")
            md.append(f"- **Description:** {tool.description}")
            md.append(f"- **Quality Score:** {tool.quality_score:.1f}/100")
            md.append(f"- **Agent-Friendly Score:** {tool.agent_friendly_score:.1f}/100")
            md.append(f"- **Trending Velocity:** {tool.trending_velocity:.1f}/100")
            md.append(f"- **GitHub:** [{tool.github_url.split('/')[-1]}]({tool.github_url})")
            md.append("")

        # Categories section
        md.append("## 📚 Tools by Category\n")
        for category, tools in sorted(report.categories.items()):
            md.append(f"### {category} ({len(tools)})\n")
            for tool in tools:
                md.append(f"- **{tool.name}** - {tool.description}")
                md.append(f"  - Score: {tool.quality_score:.1f} | Stars: {tool.stars:,}")
            md.append("")

        # Footer
        md.append("---")
        md.append(f"*Generated at {datetime.now().isoformat()}*")
        md.append("*Powered by CLI-Anything Discovery System*")

        return "\n".join(md)

    @staticmethod
    def generate_html(report: Any) -> str:
        """Generate HTML format report"""
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append("<meta charset='UTF-8'>")
        html.append("<meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html.append("<title>Daily CLI Trending Tools</title>")
        html.append("<style>")
        html.append("""
        * { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { max-width: 1000px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; }
        .header h1 { margin: 0; font-size: 2.5em; }
        .header p { margin: 10px 0 0; opacity: 0.9; }
        .card { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card h3 { margin-top: 0; color: #667eea; }
        .score { display: inline-block; background: #667eea; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold; }
        .category { display: inline-block; background: #e0e7ff; color: #667eea; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; margin-right: 5px; }
        .tools-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .tool-card { background: #f9f9f9; border-left: 4px solid #667eea; padding: 15px; border-radius: 4px; }
        .tool-card h4 { margin: 0; color: #333; }
        .tool-stats { display: flex; gap: 10px; margin-top: 10px; font-size: 0.9em; }
        .footer { text-align: center; color: #999; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; }
        """)
        html.append("</style>")
        html.append("</head>")
        html.append("<body>")

        # Header
        html.append("<div class='header'>")
        html.append("<h1>🚀 Daily CLI Trending Tools</h1>")
        html.append(f"<p>Date: {report.date}</p>")
        html.append(f"<p>Total Tools: {report.total_tools} | Average Score: {report.trending_score_avg:.1f}/100</p>")
        html.append("</div>")

        # Top tools
        html.append("<div class='card'>")
        html.append("<h2>🏆 Top 5 Trending Tools</h2>")
        for i, tool in enumerate(report.top_tools, 1):
            html.append(f"<div class='tool-card'>")
            html.append(f"<h4>{i}. {tool.name}</h4>")
            html.append(f"<p>{tool.description}</p>")
            html.append(f"<p><span class='category'>{tool.category}</span></p>")
            html.append(f"<div class='tool-stats'>")
            html.append(f"<span>Quality: <span class='score'>{tool.quality_score:.1f}</span></span>")
            html.append(f"<span>Agent-Friendly: <span class='score'>{tool.agent_friendly_score:.1f}</span></span>")
            html.append(f"<span>⭐ {tool.stars:,}</span>")
            html.append(f"</div>")
            html.append(f"</div>")
        html.append("</div>")

        # Categories
        html.append("<div class='card'>")
        html.append("<h2>📚 Tools by Category</h2>")
        for category, tools in sorted(report.categories.items()):
            html.append(f"<h3>{category} ({len(tools)})</h3>")
            html.append("<div class='tools-grid'>")
            for tool in tools:
                html.append(f"<div class='tool-card'>")
                html.append(f"<h4>{tool.name}</h4>")
                html.append(f"<p>{tool.description}</p>")
                html.append(f"<div class='tool-stats'>")
                html.append(f"<span>Score: <span class='score'>{tool.quality_score:.1f}</span></span>")
                html.append(f"<span>⭐ {tool.stars:,}</span>")
                html.append(f"</div>")
                html.append(f"</div>")
            html.append("</div>")
        html.append("</div>")

        # Footer
        html.append("<div class='footer'>")
        html.append(f"<p>Generated at {datetime.now().isoformat()}</p>")
        html.append("<p>Powered by CLI-Anything Discovery System</p>")
        html.append("</div>")

        html.append("</body>")
        html.append("</html>")

        return "\n".join(html)

    @staticmethod
    def generate_json(report: Any) -> str:
        """Generate JSON format report"""
        return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
