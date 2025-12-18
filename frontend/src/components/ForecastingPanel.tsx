import React, { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';

interface TrendingSymbol {
  symbol: string;
  mentions_24h: number;
  engagement_24h: number;
  sentiment_score: number;
  trending_rank: number;
}

interface Catalyst {
  id: string;
  symbol: string;
  title: string;
  catalyst_type: string;
  impact: string;
  days_until: number;
  expected_date: string;
}

interface Hypothesis {
  id: string;
  title: string;
  primary_symbol: string;
  direction: string;
  confidence: string;
  probability_pct: number;
  thesis: string;
}

interface ViralAlert {
  symbol: string;
  strength: string;
  buzz_score: number;
  mentions_current: number;
}

const ForecastingPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'trending' | 'catalysts' | 'hypotheses' | 'speculation'>('trending');
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [catalysts, setCatalysts] = useState<Catalyst[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [viralAlerts, setViralAlerts] = useState<ViralAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [symbolForecast, setSymbolForecast] = useState<any>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [trendingRes, catalystsRes, hypothesesRes, buzzRes] = await Promise.all([
        fetch(apiUrl('/api/forecast/sentiment/trending/symbols?limit=15')),
        fetch(apiUrl('/api/forecast/catalysts/imminent?days=14')),
        fetch(apiUrl('/api/forecast/hypothesis/active')),
        fetch(apiUrl('/api/forecast/buzz/trending?min_confidence=50')),
      ]);

      if (trendingRes.ok) {
        const data = await trendingRes.json();
        setTrendingSymbols(data.trending_symbols || []);
      }
      if (catalystsRes.ok) {
        const data = await catalystsRes.json();
        setCatalysts(data.imminent_catalysts || []);
      }
      if (hypothesesRes.ok) {
        const data = await hypothesesRes.json();
        setHypotheses(data.active_hypotheses || []);
      }
      if (buzzRes.ok) {
        const data = await buzzRes.json();
        setViralAlerts(data.trending_signals || []);
      }
    } catch (error) {
      console.error('Error fetching forecasting data:', error);
    }
    setLoading(false);
  };

  const fetchSymbolForecast = async () => {
    if (!searchSymbol.trim()) return;
    try {
      const res = await fetch(apiUrl(`/api/forecast/analysis/${searchSymbol.toUpperCase()}`));
      if (res.ok) {
        const data = await res.json();
        setSymbolForecast(data);
      }
    } catch (error) {
      console.error('Error fetching symbol forecast:', error);
    }
  };

  const getSentimentColor = (score: number) => {
    if (score >= 30) return 'text-green-400';
    if (score <= -30) return 'text-red-400';
    return 'text-yellow-400';
  };

  const getImpactBadge = (impact: string) => {
    const colors: Record<string, string> = {
      major: 'bg-red-500/20 text-red-400 border-red-500/30',
      significant: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      moderate: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      minor: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    };
    return colors[impact] || colors.minor;
  };

  const getConfidenceBadge = (confidence: string) => {
    const colors: Record<string, string> = {
      high: 'bg-green-500/20 text-green-400',
      medium: 'bg-yellow-500/20 text-yellow-400',
      low: 'bg-orange-500/20 text-orange-400',
      speculative: 'bg-purple-500/20 text-purple-400',
    };
    return colors[confidence] || colors.low;
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          🔮 Market Forecasting
        </h2>
        <button
          onClick={fetchData}
          className="px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors text-sm"
        >
          Refresh
        </button>
      </div>

      {/* Search Symbol */}
      <div className="flex gap-2 mb-6">
        <input
          type="text"
          value={searchSymbol}
          onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
          placeholder="Enter symbol (e.g., NVDA)"
          className="flex-1 px-4 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
          onKeyDown={(e) => e.key === 'Enter' && fetchSymbolForecast()}
        />
        <button
          onClick={fetchSymbolForecast}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Analyze
        </button>
      </div>

      {/* Symbol Forecast Result */}
      {symbolForecast && (
        <div className="mb-6 p-4 bg-slate-900/50 rounded-lg border border-slate-600/50">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-bold text-white">{symbolForecast.symbol} Analysis</h3>
            <button onClick={() => setSymbolForecast(null)} className="text-slate-400 hover:text-white">✕</button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center p-3 bg-slate-800/50 rounded-lg">
              <div className="text-2xl font-bold text-blue-400">{symbolForecast.forecast?.speculation_score?.toFixed(0) || 'N/A'}</div>
              <div className="text-xs text-slate-400">Speculation Score</div>
            </div>
            <div className="text-center p-3 bg-slate-800/50 rounded-lg">
              <div className={`text-2xl font-bold ${getSentimentColor(symbolForecast.sentiment?.sentiment_score || 0)}`}>
                {symbolForecast.sentiment?.sentiment_score?.toFixed(0) || 'N/A'}
              </div>
              <div className="text-xs text-slate-400">Sentiment</div>
            </div>
            <div className="text-center p-3 bg-slate-800/50 rounded-lg">
              <div className="text-2xl font-bold text-purple-400">{symbolForecast.hypothesis?.probability_pct?.toFixed(0) || 'N/A'}%</div>
              <div className="text-xs text-slate-400">Probability</div>
            </div>
            <div className="text-center p-3 bg-slate-800/50 rounded-lg">
              <div className="text-lg font-bold text-white">{symbolForecast.recommendation?.action || 'N/A'}</div>
              <div className="text-xs text-slate-400">Direction</div>
            </div>
          </div>
          {symbolForecast.hypothesis?.thesis && (
            <p className="text-sm text-slate-300">{symbolForecast.hypothesis.thesis.substring(0, 300)}...</p>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {[
          { id: 'trending', label: '📈 Trending', count: trendingSymbols.length },
          { id: 'catalysts', label: '🎯 Catalysts', count: catalysts.length },
          { id: 'hypotheses', label: '🧠 AI Hypotheses', count: hypotheses.length },
          { id: 'speculation', label: '🔥 Viral', count: viralAlerts.length },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              activeTab === tab.id
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-[300px]">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <>
            {/* Trending Symbols */}
            {activeTab === 'trending' && (
              <div className="space-y-2">
                {trendingSymbols.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No trending symbols. Add social data to start tracking.</p>
                ) : (
                  trendingSymbols.map((symbol, i) => (
                    <div key={symbol.symbol} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors">
                      <div className="flex items-center gap-3">
                        <span className="text-slate-400 text-sm w-6">#{i + 1}</span>
                        <span className="font-bold text-white">${symbol.symbol}</span>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-slate-400">{symbol.mentions_24h} mentions</span>
                        <span className={getSentimentColor(symbol.sentiment_score)}>
                          {symbol.sentiment_score > 0 ? '+' : ''}{symbol.sentiment_score.toFixed(0)}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Catalysts */}
            {activeTab === 'catalysts' && (
              <div className="space-y-2">
                {catalysts.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No imminent catalysts in the next 14 days.</p>
                ) : (
                  catalysts.map((catalyst) => (
                    <div key={catalyst.id} className="p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">${catalyst.symbol}</span>
                          <span className={`px-2 py-0.5 text-xs rounded-full border ${getImpactBadge(catalyst.impact)}`}>
                            {catalyst.impact}
                          </span>
                        </div>
                        <span className="text-sm text-slate-400">
                          {catalyst.days_until === 0 ? 'Today' : `${catalyst.days_until}d`}
                        </span>
                      </div>
                      <p className="text-sm text-slate-300">{catalyst.title}</p>
                      <p className="text-xs text-slate-500 mt-1">{catalyst.catalyst_type.replace('_', ' ')}</p>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* AI Hypotheses */}
            {activeTab === 'hypotheses' && (
              <div className="space-y-2">
                {hypotheses.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No active hypotheses. Analyze a symbol to generate.</p>
                ) : (
                  hypotheses.map((h) => (
                    <div key={h.id} className="p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">${h.primary_symbol}</span>
                          <span className={`px-2 py-0.5 text-xs rounded-full ${h.direction === 'long' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                            {h.direction.toUpperCase()}
                          </span>
                          <span className={`px-2 py-0.5 text-xs rounded-full ${getConfidenceBadge(h.confidence)}`}>
                            {h.confidence}
                          </span>
                        </div>
                        <span className="text-sm text-blue-400">{h.probability_pct.toFixed(0)}%</span>
                      </div>
                      <p className="text-sm text-slate-300">{h.title}</p>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Viral Alerts */}
            {activeTab === 'speculation' && (
              <div className="space-y-2">
                {viralAlerts.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No viral trends detected. Add social data to track.</p>
                ) : (
                  viralAlerts.map((alert, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">🔥</span>
                        <div>
                          <span className="font-bold text-white">${alert.symbol}</span>
                          <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                            alert.strength === 'viral' ? 'bg-red-500/20 text-red-400' :
                            alert.strength === 'surging' ? 'bg-orange-500/20 text-orange-400' :
                            'bg-yellow-500/20 text-yellow-400'
                          }`}>
                            {alert.strength}
                          </span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-white">{alert.buzz_score.toFixed(0)}</div>
                        <div className="text-xs text-slate-400">{alert.mentions_current} mentions/hr</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ForecastingPanel;

