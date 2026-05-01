from src.ingestion.ingestor import DataIngestor
from src.understanding.analyzer import DataUnderstandingEngine
from src.intent.detector import IntentDetector
from src.recommendation.engine import ChartRecommendationEngine
from src.rendering.pipeline import VisualizationPipeline
from src.insights.statistical import StatisticalAnalyzer

csv = (
    b"region,product,revenue,units,date\n"
    b"North,Widget A,1500,30,2024-01-01\n"
    b"South,Widget B,2200,55,2024-02-01\n"
    b"North,Widget C,900,20,2024-03-01\n"
    b"East,Widget A,3100,70,2024-04-01\n"
    b"West,Widget B,1800,40,2024-05-01\n"
)

profile = DataIngestor().ingest(csv, "test.csv")
print(f"Rows: {profile.row_count}, Cols: {profile.col_count}")

understanding = DataUnderstandingEngine().analyze(profile)
print(f"Measures: {[m.name for m in understanding.measures]}")
print(f"Dimensions: {[d.name for d in understanding.dimensions]}")
print(f"Temporals: {[t.name for t in understanding.temporals]}")

intent = IntentDetector().detect("show revenue by region", understanding)
print(f"Intent: {intent.intent.value} (confidence={intent.confidence:.2f}, tier={intent.tier})")

spec = ChartRecommendationEngine().recommend(intent, understanding)
print(f"Chart: {spec.chart_type}, x={spec.x_col}, y={spec.y_col}")

result = VisualizationPipeline().execute(profile, spec)
print(f"Render OK: chart_type={result['chart_type']}, rows_rendered={result['row_count_rendered']}")

insights = StatisticalAnalyzer().analyze(profile.df, understanding, spec)
print(f"Insights: {len(insights)} findings")
for ins in insights:
    print(f"  [{ins.severity}] {ins.description}")

print("\nSMOKE TEST PASSED")
