#!/usr/bin/env python3
"""
Daily CLI Trending Tools Discovery System
Complete entry point for the daily discovery and recommendation pipeline
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from cli_trending import CLITrendingDiscovery, DailyReport
from report_generator import ReportGenerator


class DailyTrendingSystem:
    """Main orchestration system for daily CLI trending discovery"""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.discovery = CLITrendingDiscovery()

    async def run(self):
        """Execute complete daily cycle"""
        print("=" * 60)
        print("🚀 Daily CLI Trending Tools Discovery System")
        print("=" * 60)
        print()

        # Generate report
        print("📊 Generating Daily Report...")
        report = await self.discovery.run_daily_cycle()

        # Save reports in multiple formats
        await self.save_reports(report)

        print("\n✅ Daily cycle complete!")
        print(f"📁 Reports saved to: {self.output_dir}")

    async def save_reports(self, report: DailyReport):
        """Save report in multiple formats"""
        timestamp = datetime.now().strftime("%Y%m%d")

        # JSON
        json_path = self.output_dir / f"cli_trending_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"✓ JSON report: {json_path}")

        # Markdown
        md_path = self.output_dir / f"cli_trending_{timestamp}.md"
        with open(md_path, "w") as f:
            f.write(ReportGenerator.generate_markdown(report))
        print(f"✓ Markdown report: {md_path}")

        # HTML
        html_path = self.output_dir / f"cli_trending_{timestamp}.html"
        with open(html_path, "w") as f:
            f.write(ReportGenerator.generate_html(report))
        print(f"✓ HTML report: {html_path}")

        # Summary
        summary_path = self.output_dir / "LATEST.md"
        with open(summary_path, "w") as f:
            f.write(ReportGenerator.generate_markdown(report))
        print(f"✓ Latest summary: {summary_path}")


async def main():
    """Main entry point"""
    try:
        system = DailyTrendingSystem()
        await system.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
