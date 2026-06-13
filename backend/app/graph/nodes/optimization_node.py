from ..services.renewal_service import get_renewal_analysis
from ..services.crossdeal_service import get_crossdeal_analysis
from ..services.strategic_service import analyze_strategic_opportunities


class ProcurementOptimizationNode:

    async def execute(self, state):

        renewal_analysis, renewal_summary = (
            await get_renewal_analysis()
        )

        crossdeal_analysis, crossdeal_summary = (
            await get_crossdeal_analysis()
        )

        strategic_analysis = (
            await analyze_strategic_opportunities(
                renewal_summary,
                crossdeal_summary
            )
        )

        state["optimization_analysis"] = {
            "renewal": renewal_summary,
            "crossdeal": crossdeal_summary,
            "strategic": strategic_analysis
        }

        return state