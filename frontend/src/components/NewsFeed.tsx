const mockNews = [
  { time: '12:34', ticker: 'NVDA', sentiment: 0.82, headline: 'NVIDIA H100 cleared for China sales', source: 'Reuters' },
  { time: '12:33', ticker: 'BABA', sentiment: 0.65, headline: 'Alibaba announces major buyback program', source: 'Caixin' },
  { time: '12:31', ticker: 'SAP', sentiment: 0.45, headline: 'SAP beats Q4 earnings expectations', source: 'Handelsblatt' },
  { time: '12:30', ticker: 'SPY', sentiment: 0.12, headline: 'Fed signals potential rate pause in Q1', source: 'WSJ' },
  { time: '12:28', ticker: 'TSLA', sentiment: -0.33, headline: 'Tesla recalls 500K vehicles for safety update', source: 'CNN' },
]

export function NewsFeed() {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h2 className="mb-4 text-lg font-semibold">Live News Feed (Global)</h2>
      <div className="space-y-2">
        {mockNews.map((news, index) => (
          <div
            key={index}
            className="flex items-center gap-4 rounded-lg bg-secondary/30 px-3 py-2"
          >
            <span className="text-sm text-muted-foreground">[{news.time}]</span>
            <span className="w-12 font-medium">{news.ticker}</span>
            <span
              className={`w-12 text-sm ${
                news.sentiment > 0 ? 'text-profit' : news.sentiment < 0 ? 'text-loss' : 'text-muted-foreground'
              }`}
            >
              {news.sentiment > 0 ? '+' : ''}{news.sentiment.toFixed(2)}
            </span>
            <span className="flex-1 text-sm">"{news.headline}"</span>
            <span className="text-sm text-muted-foreground">- {news.source}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

