import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import { apiUrl } from '../config/api';
import { TrendingUp, TrendingDown, Target, Calendar, Zap, Brain, Activity, AlertCircle, ExternalLink, Info, ChevronDown, ChevronUp, Newspaper, Shield, BarChart3 } from 'lucide-react';

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

interface ProjectionData {
  symbol: string;
  current_price: number;
  confidence: string;
  historical: { date: string; value: number; is_projection: boolean }[];
  projection_1m: { date: string; value: number; low: number; high: number }[];
  projection_3m: { date: string; value: number; low: number; high: number }[];
  projection_6m: { date: string; value: number; low: number; high: number }[];
  projection_1y: { date: string; value: number; low: number; high: number }[];
  target_1m: { low: number; mid: number; high: number };
  target_3m: { low: number; mid: number; high: number };
  target_6m: { low: number; mid: number; high: number };
  target_1y: { low: number; mid: number; high: number };
  analyst_targets: { low: number; mean: number; high: number; num_analysts: number; recommendation: string };
  trend_direction: string;
  trend_strength: number;
  volatility: number;
}

interface NewsReference {
  title: string;
  url: string;
  source: string;
  published: string;
  relevance: string;
  sentiment_impact: string;
}

interface ScoreBreakdown {
  component: string;
  value: number;
  weight: number;
  contribution: number;
  explanation: string;
  sources: string[];
}

interface AnalysisWithSources {
  symbol: string;
  current_price: number;
  speculation_score: number;
  sentiment_score: number;
  probability_pct: number;
  trend_direction: string;
  score_breakdown: ScoreBreakdown[];
  news_articles: NewsReference[];
  bullish_factors: string[];
  bearish_factors: string[];
  methodology: Record<string, string>;
  data_sources: { name: string; type: string; reliability: string }[];
  reliability: {
    overall: string;
    news_coverage: number;
    data_freshness: string;
    confidence_factors: Record<string, boolean>;
    disclaimer: string;
  };
  updated_at: string;
}

type TimeHorizon = '1m' | '3m' | '6m' | '1y';

const ForecastingPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'projections' | 'trending' | 'catalysts' | 'hypotheses' | 'speculation'>('projections');
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [catalysts, setCatalysts] = useState<Catalyst[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [viralAlerts, setViralAlerts] = useState<ViralAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [projectionLoading, setProjectionLoading] = useState(false);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [projectionData, setProjectionData] = useState<ProjectionData | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalysisWithSources | null>(null);
  const [selectedHorizon, setSelectedHorizon] = useState<TimeHorizon>('6m');
  const [error, setError] = useState<string | null>(null);
  const [showMethodology, setShowMethodology] = useState(false);
  const [showScoreBreakdown, setShowScoreBreakdown] = useState(false);

  // Chart refs
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

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

  const fetchProjections = useCallback(async (symbol: string) => {
    if (!symbol.trim()) return;
    
    setProjectionLoading(true);
    setError(null);
    setAnalysisData(null);
    
    try {
      // Fetch both projections and analysis with sources in parallel
      const [projRes, analysisRes] = await Promise.all([
        fetch(apiUrl(`/api/forecast/projections/${symbol.toUpperCase()}?history_period=1y`)),
        fetch(apiUrl(`/api/forecast/analysis-with-sources/${symbol.toUpperCase()}`)),
      ]);
      
      if (projRes.ok) {
        const data = await projRes.json();
        setProjectionData(data);
      } else {
        const errData = await projRes.json();
        setError(errData.detail || 'Failed to fetch projections');
      }
      
      if (analysisRes.ok) {
        const data = await analysisRes.json();
        setAnalysisData(data);
      }
    } catch (error) {
      setError('Network error. Please try again.');
      console.error('Error fetching projections:', error);
    }
    setProjectionLoading(false);
  }, []);

  // Create projection chart
  useEffect(() => {
    if (!chartContainerRef.current || !projectionData) return;

    // Cleanup
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.03)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 350,
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
      },
      crosshair: {
        mode: 1,
        vertLine: { color: 'rgba(139, 92, 246, 0.4)', width: 1, style: 2 },
        horzLine: { color: 'rgba(139, 92, 246, 0.4)', width: 1, style: 2 },
      },
    });

    chartRef.current = chart;

    // Get projection data for selected horizon
    const projectionKey = `projection_${selectedHorizon}` as keyof ProjectionData;
    const projections = projectionData[projectionKey] as { date: string; value: number; low: number; high: number }[];

    // Historical area series
    const historicalSeries = chart.addAreaSeries({
      lineColor: '#3b82f6',
      topColor: 'rgba(59, 130, 246, 0.3)',
      bottomColor: 'rgba(59, 130, 246, 0.0)',
      lineWidth: 2,
    });

    historicalSeries.setData(
      projectionData.historical.map(d => ({
        time: d.date as Time,
        value: d.value,
      }))
    );

    // Projection line (main forecast)
    if (projections && projections.length > 0) {
      const projectionSeries = chart.addLineSeries({
        color: '#22c55e',
        lineWidth: 2,
        lineStyle: 2, // Dashed
        lastValueVisible: true,
        priceLineVisible: false,
      });

      // Connect from last historical point
      const lastHistorical = projectionData.historical[projectionData.historical.length - 1];
      projectionSeries.setData([
        { time: lastHistorical.date as Time, value: lastHistorical.value },
        ...projections.map(d => ({
          time: d.date as Time,
          value: d.value,
        }))
      ]);

      // Upper confidence band
      const upperBandSeries = chart.addLineSeries({
        color: 'rgba(34, 197, 94, 0.3)',
        lineWidth: 1,
        lineStyle: 3, // Dotted
        priceLineVisible: false,
        lastValueVisible: false,
      });

      upperBandSeries.setData([
        { time: lastHistorical.date as Time, value: lastHistorical.value },
        ...projections.map(d => ({
          time: d.date as Time,
          value: d.high,
        }))
      ]);

      // Lower confidence band
      const lowerBandSeries = chart.addLineSeries({
        color: 'rgba(239, 68, 68, 0.3)',
        lineWidth: 1,
        lineStyle: 3,
        priceLineVisible: false,
        lastValueVisible: false,
      });

      lowerBandSeries.setData([
        { time: lastHistorical.date as Time, value: lastHistorical.value },
        ...projections.map(d => ({
          time: d.date as Time,
          value: d.low,
        }))
      ]);

      // Analyst target line (if available)
      if (projectionData.analyst_targets.mean > 0) {
        const analystLine = chart.addLineSeries({
          color: '#f59e0b',
          lineWidth: 1,
          lineStyle: 0, // Solid
          priceLineVisible: false,
          lastValueVisible: true,
        });

        const lastProjection = projections[projections.length - 1];
        analystLine.setData([
          { time: lastHistorical.date as Time, value: projectionData.analyst_targets.mean },
          { time: lastProjection.date as Time, value: projectionData.analyst_targets.mean },
        ]);
      }
    }

    chart.timeScale().fitContent();

    // Resize handler
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [projectionData, selectedHorizon]);

  const getTargetData = () => {
    if (!projectionData) return null;
    const key = `target_${selectedHorizon}` as keyof ProjectionData;
    return projectionData[key] as { low: number; mid: number; high: number };
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

  const targetData = getTargetData();

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

      {/* Tabs */}
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {[
          { id: 'projections', label: '📈 Projections', icon: <TrendingUp className="w-4 h-4" /> },
          { id: 'trending', label: '🔥 Trending', count: trendingSymbols.length },
          { id: 'catalysts', label: '🎯 Catalysts', count: catalysts.length },
          { id: 'hypotheses', label: '🧠 AI Hypotheses', count: hypotheses.length },
          { id: 'speculation', label: '⚡ Viral', count: viralAlerts.length },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors flex items-center gap-2 ${
              activeTab === tab.id
                ? 'bg-violet-600 text-white'
                : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {tab.label} {tab.count !== undefined && `(${tab.count})`}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-[400px]">
        {/* Projections Tab */}
        {activeTab === 'projections' && (
          <div className="space-y-4">
            {/* Search */}
            <div className="flex gap-2">
              <input
                type="text"
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
                placeholder="Enter symbol for projection (e.g., NVDA, AAPL)"
                className="flex-1 px-4 py-2.5 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-violet-500"
                onKeyDown={(e) => e.key === 'Enter' && fetchProjections(searchSymbol)}
              />
              <button
                onClick={() => fetchProjections(searchSymbol)}
                disabled={projectionLoading || !searchSymbol}
                className="px-6 py-2 bg-violet-600 hover:bg-violet-700 disabled:bg-slate-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                {projectionLoading ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <Target className="w-4 h-4" />
                    Forecast
                  </>
                )}
              </button>
            </div>

            {/* Quick symbols */}
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-slate-500">Quick:</span>
              {['NVDA', 'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META'].map(sym => (
                <button
                  key={sym}
                  onClick={() => { setSearchSymbol(sym); fetchProjections(sym); }}
                  className="px-2 py-1 text-xs bg-slate-700/50 hover:bg-slate-600 text-slate-400 hover:text-white rounded transition-colors"
                >
                  {sym}
                </button>
              ))}
            </div>

            {/* Error */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}

            {/* Projection Results */}
            {projectionData && (
              <>
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-bold text-white">${projectionData.symbol}</span>
                    <span className="text-xl text-slate-300">${projectionData.current_price.toFixed(2)}</span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      projectionData.trend_direction === 'bullish' 
                        ? 'bg-green-500/20 text-green-400'
                        : projectionData.trend_direction === 'bearish'
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-slate-500/20 text-slate-400'
                    }`}>
                      {projectionData.trend_direction === 'bullish' ? <TrendingUp className="w-3 h-3 inline mr-1" /> : 
                       projectionData.trend_direction === 'bearish' ? <TrendingDown className="w-3 h-3 inline mr-1" /> : null}
                      {projectionData.trend_direction.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">Volatility:</span>
                    <span className={`text-sm font-medium ${
                      projectionData.volatility > 40 ? 'text-red-400' :
                      projectionData.volatility > 25 ? 'text-yellow-400' : 'text-green-400'
                    }`}>
                      {projectionData.volatility.toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Time Horizon Selector */}
                <div className="flex items-center gap-2 bg-slate-800/50 p-1 rounded-lg w-fit">
                  {[
                    { id: '1m', label: '1 Month' },
                    { id: '3m', label: '3 Months' },
                    { id: '6m', label: '6 Months' },
                    { id: '1y', label: '1 Year' },
                  ].map(h => (
                    <button
                      key={h.id}
                      onClick={() => setSelectedHorizon(h.id as TimeHorizon)}
                      className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                        selectedHorizon === h.id
                          ? 'bg-violet-600 text-white'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      {h.label}
                    </button>
                  ))}
                </div>

                {/* Chart */}
                <div ref={chartContainerRef} className="rounded-lg overflow-hidden bg-slate-900/30" />

                {/* Legend */}
                <div className="flex flex-wrap items-center gap-4 text-xs">
                  <div className="flex items-center gap-1.5">
                    <div className="w-4 h-0.5 bg-blue-500"></div>
                    <span className="text-slate-400">Historical</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-4 h-0.5 bg-green-500" style={{ borderStyle: 'dashed' }}></div>
                    <span className="text-slate-400">Projected</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-4 h-0.5 bg-green-500/30"></div>
                    <span className="text-slate-400">Upper Band</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-4 h-0.5 bg-red-500/30"></div>
                    <span className="text-slate-400">Lower Band</span>
                  </div>
                  {projectionData.analyst_targets.mean > 0 && (
                    <div className="flex items-center gap-1.5">
                      <div className="w-4 h-0.5 bg-amber-500"></div>
                      <span className="text-slate-400">Analyst Target</span>
                    </div>
                  )}
                </div>

                {/* Target Prices */}
                {targetData && (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 bg-slate-800/50 rounded-lg text-center border border-red-500/20">
                      <div className="text-xs text-slate-500 mb-1">Bear Case</div>
                      <div className="text-xl font-bold text-red-400">${targetData.low.toFixed(2)}</div>
                      <div className="text-xs text-slate-500">
                        {(((targetData.low - projectionData.current_price) / projectionData.current_price) * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="p-4 bg-slate-800/50 rounded-lg text-center border border-green-500/20">
                      <div className="text-xs text-slate-500 mb-1">Base Case</div>
                      <div className="text-2xl font-bold text-green-400">${targetData.mid.toFixed(2)}</div>
                      <div className="text-xs text-slate-500">
                        {(((targetData.mid - projectionData.current_price) / projectionData.current_price) * 100) > 0 ? '+' : ''}
                        {(((targetData.mid - projectionData.current_price) / projectionData.current_price) * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="p-4 bg-slate-800/50 rounded-lg text-center border border-blue-500/20">
                      <div className="text-xs text-slate-500 mb-1">Bull Case</div>
                      <div className="text-xl font-bold text-blue-400">${targetData.high.toFixed(2)}</div>
                      <div className="text-xs text-slate-500">
                        +{(((targetData.high - projectionData.current_price) / projectionData.current_price) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                )}

                {/* Analyst Targets */}
                {projectionData.analyst_targets.mean > 0 && (
                  <div className="p-4 bg-amber-500/10 rounded-lg border border-amber-500/30">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Target className="w-4 h-4 text-amber-400" />
                        <span className="text-sm font-medium text-amber-400">Analyst Consensus</span>
                        <span className="text-xs text-slate-500">({projectionData.analyst_targets.num_analysts} analysts)</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        projectionData.analyst_targets.recommendation === 'buy' || projectionData.analyst_targets.recommendation === 'strong_buy'
                          ? 'bg-green-500/20 text-green-400'
                          : projectionData.analyst_targets.recommendation === 'sell' || projectionData.analyst_targets.recommendation === 'strong_sell'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-slate-500/20 text-slate-400'
                      }`}>
                        {projectionData.analyst_targets.recommendation.toUpperCase().replace('_', ' ')}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 mt-3">
                      <div className="text-center">
                        <div className="text-xs text-slate-500">Low</div>
                        <div className="text-lg font-bold text-white">${projectionData.analyst_targets.low.toFixed(2)}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-slate-500">Mean Target</div>
                        <div className="text-xl font-bold text-amber-400">${projectionData.analyst_targets.mean.toFixed(2)}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-slate-500">High</div>
                        <div className="text-lg font-bold text-white">${projectionData.analyst_targets.high.toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Analysis with Sources */}
                {analysisData && (
                  <>
                    {/* Bullish/Bearish Factors */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Bullish Factors */}
                      <div className="p-4 bg-green-500/5 rounded-lg border border-green-500/20">
                        <div className="flex items-center gap-2 mb-3">
                          <TrendingUp className="w-4 h-4 text-green-400" />
                          <span className="text-sm font-medium text-green-400">Bullish Factors</span>
                        </div>
                        {analysisData.bullish_factors.length > 0 ? (
                          <ul className="space-y-2">
                            {analysisData.bullish_factors.map((factor, i) => (
                              <li key={i} className="text-sm text-slate-300">{factor}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-slate-500">No strong bullish signals detected</p>
                        )}
                      </div>
                      
                      {/* Bearish Factors */}
                      <div className="p-4 bg-red-500/5 rounded-lg border border-red-500/20">
                        <div className="flex items-center gap-2 mb-3">
                          <TrendingDown className="w-4 h-4 text-red-400" />
                          <span className="text-sm font-medium text-red-400">Bearish Factors</span>
                        </div>
                        {analysisData.bearish_factors.length > 0 ? (
                          <ul className="space-y-2">
                            {analysisData.bearish_factors.map((factor, i) => (
                              <li key={i} className="text-sm text-slate-300">{factor}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-slate-500">No strong bearish signals detected</p>
                        )}
                      </div>
                    </div>

                    {/* News References */}
                    {analysisData.news_articles.length > 0 && (
                      <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-3">
                          <Newspaper className="w-4 h-4 text-blue-400" />
                          <span className="text-sm font-medium text-white">News & References</span>
                          <span className="text-xs text-slate-500">({analysisData.news_articles.length} articles)</span>
                        </div>
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                          {analysisData.news_articles.map((article, i) => (
                            <a
                              key={i}
                              href={article.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="block p-3 bg-slate-900/50 rounded-lg hover:bg-slate-900 transition-colors group"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1">
                                  <p className="text-sm text-white group-hover:text-blue-400 transition-colors line-clamp-2">
                                    {article.title}
                                  </p>
                                  <div className="flex items-center gap-2 mt-1">
                                    <span className="text-xs text-slate-500">{article.source}</span>
                                    <span className="text-xs text-slate-600">•</span>
                                    <span className="text-xs text-slate-500">
                                      {new Date(article.published).toLocaleDateString()}
                                    </span>
                                    <span className={`px-1.5 py-0.5 text-xs rounded ${
                                      article.sentiment_impact === 'bullish' 
                                        ? 'bg-green-500/20 text-green-400'
                                        : article.sentiment_impact === 'bearish'
                                        ? 'bg-red-500/20 text-red-400'
                                        : 'bg-slate-500/20 text-slate-400'
                                    }`}>
                                      {article.sentiment_impact}
                                    </span>
                                  </div>
                                </div>
                                <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-blue-400 flex-shrink-0" />
                              </div>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Score Breakdown (Collapsible) */}
                    <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
                      <button
                        onClick={() => setShowScoreBreakdown(!showScoreBreakdown)}
                        className="w-full flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <BarChart3 className="w-4 h-4 text-violet-400" />
                          <span className="text-sm font-medium text-white">Score Breakdown</span>
                          <span className="text-xs text-slate-500">How is this calculated?</span>
                        </div>
                        {showScoreBreakdown ? (
                          <ChevronUp className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        )}
                      </button>
                      
                      {showScoreBreakdown && (
                        <div className="mt-4 space-y-3">
                          {analysisData.score_breakdown.map((score, i) => (
                            <div key={i} className="p-3 bg-slate-900/50 rounded-lg">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium text-white">{score.component}</span>
                                <div className="flex items-center gap-2">
                                  <span className="text-sm text-slate-400">
                                    {score.value.toFixed(0)}/100
                                  </span>
                                  <span className="text-xs text-slate-500">
                                    (×{score.weight.toFixed(2)})
                                  </span>
                                </div>
                              </div>
                              <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden mb-2">
                                <div
                                  className="h-full bg-gradient-to-r from-violet-500 to-blue-500 rounded-full"
                                  style={{ width: `${score.value}%` }}
                                />
                              </div>
                              <p className="text-xs text-slate-400 mb-2">{score.explanation}</p>
                              <div className="flex flex-wrap gap-1">
                                {score.sources.map((src, j) => (
                                  <span key={j} className="px-1.5 py-0.5 bg-slate-700/50 text-xs text-slate-500 rounded">
                                    {src}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Methodology (Collapsible) */}
                    <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
                      <button
                        onClick={() => setShowMethodology(!showMethodology)}
                        className="w-full flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <Info className="w-4 h-4 text-cyan-400" />
                          <span className="text-sm font-medium text-white">Methodology & Sources</span>
                        </div>
                        {showMethodology ? (
                          <ChevronUp className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        )}
                      </button>
                      
                      {showMethodology && (
                        <div className="mt-4 space-y-4">
                          {/* Methodology */}
                          <div className="space-y-2">
                            {Object.entries(analysisData.methodology).map(([key, value]) => (
                              <div key={key} className="p-2 bg-slate-900/50 rounded">
                                <span className="text-xs font-medium text-violet-400 uppercase">{key.replace('_', ' ')}</span>
                                <p className="text-xs text-slate-400 mt-1">{value}</p>
                              </div>
                            ))}
                          </div>
                          
                          {/* Data Sources */}
                          <div>
                            <span className="text-xs font-medium text-slate-500 uppercase">Data Sources</span>
                            <div className="mt-2 grid grid-cols-2 gap-2">
                              {analysisData.data_sources.map((source, i) => (
                                <div key={i} className="p-2 bg-slate-900/50 rounded flex items-center justify-between">
                                  <div>
                                    <span className="text-xs text-white">{source.name}</span>
                                    <span className="text-xs text-slate-500 ml-1">({source.type})</span>
                                  </div>
                                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                                    source.reliability === 'High' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                                  }`}>
                                    {source.reliability}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                          
                          {/* Reliability */}
                          <div className="p-3 bg-slate-900/50 rounded-lg">
                            <div className="flex items-center gap-2 mb-2">
                              <Shield className="w-4 h-4 text-slate-400" />
                              <span className="text-xs font-medium text-white">Reliability Assessment</span>
                              <span className={`px-1.5 py-0.5 text-xs rounded ${
                                analysisData.reliability.overall === 'high' 
                                  ? 'bg-green-500/20 text-green-400'
                                  : analysisData.reliability.overall === 'medium'
                                  ? 'bg-yellow-500/20 text-yellow-400'
                                  : 'bg-red-500/20 text-red-400'
                              }`}>
                                {analysisData.reliability.overall.toUpperCase()}
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-2 mb-2">
                              {Object.entries(analysisData.reliability.confidence_factors).map(([key, value]) => (
                                <span key={key} className={`px-2 py-1 text-xs rounded ${
                                  value ? 'bg-green-500/10 text-green-400' : 'bg-slate-700 text-slate-500'
                                }`}>
                                  {value ? '✓' : '✗'} {key.replace(/_/g, ' ')}
                                </span>
                              ))}
                            </div>
                            <p className="text-xs text-slate-500 italic">{analysisData.reliability.disclaimer}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </>
            )}

            {/* Empty State */}
            {!projectionData && !projectionLoading && !error && (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800/50 flex items-center justify-center">
                  <TrendingUp className="w-8 h-8 text-slate-600" />
                </div>
                <h3 className="text-lg font-medium text-white mb-2">Price Projections</h3>
                <p className="text-slate-500 text-sm max-w-md mx-auto">
                  Enter a stock symbol to see extrapolated price forecasts for 1 month, 3 months, 6 months, and 1 year into the future.
                </p>
              </div>
            )}
          </div>
        )}

        {loading ? (
          activeTab !== 'projections' && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          )
        ) : (
          <>
            {/* Trending Symbols */}
            {activeTab === 'trending' && (
              <div className="space-y-2">
                {trendingSymbols.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No trending symbols. Add social data to start tracking.</p>
                ) : (
                  trendingSymbols.map((symbol, i) => (
                    <div key={symbol.symbol} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer"
                      onClick={() => { setSearchSymbol(symbol.symbol); setActiveTab('projections'); fetchProjections(symbol.symbol); }}>
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
