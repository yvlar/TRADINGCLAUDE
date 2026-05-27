import { useQuery } from '@tanstack/react-query'
import { LineChart, Line } from 'recharts'
import { getCompositeHistory } from '../api/analyze'
import { CHART } from '../lib/colors'

interface CompositeSparklineProps {
  ticker: string
  height?: number
}

export function CompositeSparkline({ ticker, height = 40 }: CompositeSparklineProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['composite-history', ticker],
    queryFn: () => getCompositeHistory(ticker, 30),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div
        data-testid="sparkline-loading"
        className="animate-pulse bg-muted rounded"
        style={{ width: 120, height }}
      />
    )
  }

  if (isError || !data || data.length === 0) {
    return <span className="text-muted-foreground text-sm">—</span>
  }

  const chartData = data.map((pt) => ({ score: pt.score }))

  return (
    <div data-testid="sparkline-container" style={{ height }}>
      <LineChart data={chartData} width={120} height={height} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
        <Line
          type="monotone"
          dataKey="score"
          stroke={CHART.line}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </div>
  )
}
