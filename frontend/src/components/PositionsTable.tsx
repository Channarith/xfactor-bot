const mockPositions = [
  { symbol: 'NVDA', qty: 100, pnl: 2345.67, strategy: 'News+Tech' },
  { symbol: 'AAPL', qty: 200, pnl: 890.12, strategy: 'Momentum' },
  { symbol: 'TSLA', qty: -50, pnl: -234.56, strategy: 'MeanRev' },
  { symbol: 'MSFT', qty: 150, pnl: 1234.00, strategy: 'Technical' },
  { symbol: 'AMD', qty: 300, pnl: 567.89, strategy: 'News' },
]

export function PositionsTable() {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h2 className="mb-4 text-lg font-semibold">Positions</h2>
      <table className="w-full">
        <thead>
          <tr className="border-b border-border text-left text-sm text-muted-foreground">
            <th className="pb-2">Symbol</th>
            <th className="pb-2">Qty</th>
            <th className="pb-2">P&L</th>
            <th className="pb-2">Strategy</th>
          </tr>
        </thead>
        <tbody>
          {mockPositions.map((pos) => (
            <tr key={pos.symbol} className="border-b border-border/50">
              <td className="py-2 font-medium">{pos.symbol}</td>
              <td className="py-2">{pos.qty}</td>
              <td className={`py-2 ${pos.pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toLocaleString()}
              </td>
              <td className="py-2 text-muted-foreground">{pos.strategy}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

