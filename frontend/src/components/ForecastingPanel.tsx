import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import { apiUrl } from '../config/api';
import { TrendingUp, TrendingDown, Target, Calendar, Zap, Brain, Activity, AlertCircle, ExternalLink, Info, ChevronDown, ChevronUp, Newspaper, Shield, BarChart3, RefreshCw, Download, Loader2, Search } from 'lucide-react';

interface SymbolSearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

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
  formula?: string;
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

interface AIPatternPrediction {
  pattern: string;
  type: 'bullish' | 'bearish' | 'neutral';
  confidence: number;
  timeframe: string;
  target_price?: number;
  stop_loss?: number;
  description: string;
  trigger: string;
}

type TimeHorizon = '1m' | '3m' | '6m' | '1y';

interface FetchStatus {
  is_fetching: boolean;
  last_fetch: string | null;
  progress: string;
  symbols_processed: number;
  total_symbols: number;
  error: string | null;
}

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
  
  // Force fetch state
  const [fetchStatus, setFetchStatus] = useState<FetchStatus | null>(null);
  const [isForceFetching, setIsForceFetching] = useState(false);
  
  // Symbol search autocomplete state
  const [searchSuggestions, setSearchSuggestions] = useState<SymbolSearchResult[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Chart refs
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced symbol search
  const searchSymbols = useCallback(async (query: string) => {
    if (query.length < 1) {
      setSearchSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    
    setSearchLoading(true);
    try {
      const response = await fetch(apiUrl(`/api/symbols/search?q=${encodeURIComponent(query)}&limit=10`));
      if (response.ok) {
        const data = await response.json();
        setSearchSuggestions(data.results || []);
        setShowSuggestions(true);
      }
    } catch (e) {
      console.error('Error searching symbols:', e);
    }
    setSearchLoading(false);
  }, []);

  const handleSearchChange = (value: string) => {
    setSearchSymbol(value.toUpperCase());
    
    // Debounce the search
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = setTimeout(() => {
      searchSymbols(value);
    }, 300);
  };

  const selectSymbol = (symbol: string) => {
    setSearchSymbol(symbol);
    setShowSuggestions(false);
    setSearchSuggestions([]);
    fetchProjections(symbol);
  };

  useEffect(() => {
    fetchData();
    checkFetchStatus();
  }, []);
  
  // Poll fetch status while fetching
  useEffect(() => {
    if (!isForceFetching) return;
    
    const interval = setInterval(async () => {
      const status = await checkFetchStatus();
      if (status && !status.is_fetching) {
        setIsForceFetching(false);
        // Refresh data after fetch completes
        fetchData();
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [isForceFetching]);
  
  const checkFetchStatus = async () => {
    try {
      const res = await fetch(apiUrl('/api/forecast/fetch-status'));
      if (res.ok) {
        const data = await res.json();
        setFetchStatus(data);
        return data;
      }
    } catch (e) {
      console.error('Error checking fetch status:', e);
    }
    return null;
  };
  
  const forceFetchData = async () => {
    try {
      setIsForceFetching(true);
      const res = await fetch(apiUrl('/api/forecast/force-fetch'), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        console.log('Force fetch started:', data);
      }
    } catch (e) {
      console.error('Error starting force fetch:', e);
      setIsForceFetching(false);
    }
  };

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

  // Generate AI pattern predictions based on price data
  const generatePatternPredictions = useCallback((): AIPatternPrediction[] => {
    if (!projectionData) return [];
    
    const predictions: AIPatternPrediction[] = [];
    const { current_price, trend_direction, trend_strength, volatility, analyst_targets } = projectionData;
    const targetData = getTargetData();
    
    // Calculate price momentum from historical data
    const historical = projectionData.historical;
    const recentPrices = historical.slice(-20);
    const oldPrices = historical.slice(-40, -20);
    const recentAvg = recentPrices.reduce((a, b) => a + b.value, 0) / recentPrices.length;
    const oldAvg = oldPrices.length > 0 ? oldPrices.reduce((a, b) => a + b.value, 0) / oldPrices.length : recentAvg;
    const momentum = ((recentAvg - oldAvg) / oldAvg) * 100;
    
    // Pattern 1: Trend Continuation or Reversal
    if (trend_strength > 60) {
      predictions.push({
        pattern: trend_direction === 'bullish' ? 'Strong Uptrend Continuation' : 'Strong Downtrend Continuation',
        type: trend_direction === 'bullish' ? 'bullish' : 'bearish',
        confidence: Math.min(85, 50 + trend_strength * 0.5),
        timeframe: '2-4 weeks',
        target_price: trend_direction === 'bullish' ? targetData?.mid : targetData?.low,
        description: `Strong ${trend_direction} trend detected with ${trend_strength.toFixed(0)}% strength. Momentum indicators confirm continuation.`,
        trigger: trend_direction === 'bullish' 
          ? `Price holds above $${(current_price * 0.97).toFixed(2)} support`
          : `Price stays below $${(current_price * 1.03).toFixed(2)} resistance`,
      });
    }
    
    // Pattern 2: Breakout Detection
    if (volatility < 25 && trend_strength > 40) {
      const breakoutDirection = trend_direction === 'bullish' ? 'bullish' : 'bearish';
      predictions.push({
        pattern: 'Volatility Squeeze Breakout',
        type: breakoutDirection,
        confidence: Math.min(75, 55 + (25 - volatility)),
        timeframe: '1-2 weeks',
        target_price: breakoutDirection === 'bullish' ? current_price * 1.08 : current_price * 0.92,
        stop_loss: breakoutDirection === 'bullish' ? current_price * 0.96 : current_price * 1.04,
        description: `Low volatility (${volatility.toFixed(1)}%) suggests accumulation phase. Breakout expected soon.`,
        trigger: breakoutDirection === 'bullish'
          ? `Break above $${(current_price * 1.02).toFixed(2)} with volume`
          : `Break below $${(current_price * 0.98).toFixed(2)} with volume`,
      });
    }
    
    // Pattern 3: Mean Reversion
    if (Math.abs(momentum) > 8) {
      const isOverextended = momentum > 8;
      predictions.push({
        pattern: isOverextended ? 'Overbought Pullback' : 'Oversold Bounce',
        type: isOverextended ? 'bearish' : 'bullish',
        confidence: Math.min(70, 45 + Math.abs(momentum) * 2),
        timeframe: '3-7 days',
        target_price: isOverextended ? current_price * 0.95 : current_price * 1.05,
        description: `Price has moved ${Math.abs(momentum).toFixed(1)}% from 20-day mean. ${isOverextended ? 'Pullback' : 'Bounce'} likely.`,
        trigger: isOverextended
          ? `RSI divergence or bearish candlestick pattern`
          : `RSI bounce from oversold or bullish reversal candle`,
      });
    }
    
    // Pattern 4: Support/Resistance Test
    if (targetData) {
      const nearSupport = current_price < targetData.mid * 0.98;
      const nearResistance = current_price > targetData.mid * 1.02;
      
      if (nearSupport || nearResistance) {
        predictions.push({
          pattern: nearSupport ? 'Support Level Test' : 'Resistance Level Test',
          type: nearSupport ? 'bullish' : 'neutral',
          confidence: 65,
          timeframe: '1-2 weeks',
          target_price: nearSupport ? targetData.mid : targetData.high,
          stop_loss: nearSupport ? targetData.low * 0.98 : targetData.mid,
          description: nearSupport 
            ? `Testing key support near $${targetData.low.toFixed(2)}. Bounce opportunity if held.`
            : `Approaching resistance near $${targetData.high.toFixed(2)}. Watch for breakout or rejection.`,
          trigger: nearSupport
            ? `Bullish candle pattern at support with increasing volume`
            : `Break above $${targetData.high.toFixed(2)} or rejection candle`,
        });
      }
    }
    
    // Pattern 5: Analyst Divergence
    if (analyst_targets.mean > 0) {
      const analystUpside = ((analyst_targets.mean - current_price) / current_price) * 100;
      if (Math.abs(analystUpside) > 15) {
        predictions.push({
          pattern: analystUpside > 15 ? 'Analyst Upgrade Potential' : 'Analyst Downgrade Risk',
          type: analystUpside > 15 ? 'bullish' : 'bearish',
          confidence: Math.min(70, 50 + Math.abs(analystUpside) * 0.5),
          timeframe: '1-3 months',
          target_price: analyst_targets.mean,
          description: analystUpside > 15
            ? `${analyst_targets.num_analysts} analysts see ${analystUpside.toFixed(0)}% upside. Consensus: ${analyst_targets.recommendation.replace('_', ' ')}`
            : `Price ${Math.abs(analystUpside).toFixed(0)}% above analyst mean target. Downside risk.`,
          trigger: analystUpside > 15
            ? `Positive earnings or product announcement`
            : `Earnings miss or guidance cut`,
        });
      }
    }
    
    // Pattern 6: Momentum Divergence
    if (trend_direction === 'bullish' && momentum < 0) {
      predictions.push({
        pattern: 'Bearish Momentum Divergence',
        type: 'bearish',
        confidence: 60,
        timeframe: '1-3 weeks',
        target_price: targetData?.low,
        description: 'Price in uptrend but momentum weakening. Potential trend reversal forming.',
        trigger: 'Break below recent swing low or MACD cross',
      });
    } else if (trend_direction === 'bearish' && momentum > 0) {
      predictions.push({
        pattern: 'Bullish Momentum Divergence',
        type: 'bullish',
        confidence: 60,
        timeframe: '1-3 weeks',
        target_price: targetData?.mid,
        description: 'Price in downtrend but momentum improving. Potential bottom forming.',
        trigger: 'Break above recent swing high or MACD cross',
      });
    }
    
    // Sort by confidence
    return predictions.sort((a, b) => b.confidence - a.confidence).slice(0, 4);
  }, [projectionData, selectedHorizon]);

  const targetData = getTargetData();
  const patternPredictions = generatePatternPredictions();

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          🔮 Market Forecasting
        </h2>
        <div className="flex items-center gap-2">
          {/* Force Fetch Button */}
          <button
            onClick={forceFetchData}
            disabled={isForceFetching}
            className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 transition-colors ${
              isForceFetching 
                ? 'bg-amber-500/20 text-amber-400 cursor-wait'
                : 'bg-violet-500/20 text-violet-400 hover:bg-violet-500/30'
            }`}
            title="Fetch real data from yfinance for trending, catalysts, and hypotheses"
          >
            {isForceFetching ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>
                  Fetching {fetchStatus?.symbols_processed || 0}/{fetchStatus?.total_symbols || 30}...
                </span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>Force Fetch</span>
              </>
            )}
          </button>
          
          {/* Refresh Button */}
          <button
            onClick={fetchData}
            className="px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors text-sm flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
        </div>
      </div>
      
      {/* Fetch Status Banner */}
      {fetchStatus?.last_fetch && !isForceFetching && (
        <div className="mb-4 px-3 py-2 bg-slate-700/30 rounded-lg flex items-center justify-between text-xs text-slate-400">
          <span>
            Last updated: {new Date(fetchStatus.last_fetch).toLocaleString()}
          </span>
          <span>
            {trendingSymbols.length} trending • {catalysts.length} catalysts • {hypotheses.length} hypotheses
          </span>
        </div>
      )}
      
      {/* Show empty state message if no data */}
      {!isForceFetching && trendingSymbols.length === 0 && catalysts.length === 0 && hypotheses.length === 0 && (
        <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-amber-400 font-medium">No forecasting data available</p>
            <p className="text-xs text-slate-400">Click "Force Fetch" to analyze 30 popular stocks and populate trending symbols, catalysts, and AI hypotheses.</p>
          </div>
        </div>
      )}

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
            {/* Search with Autocomplete */}
            <div className="flex gap-2">
              <div ref={searchContainerRef} className="relative flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={searchSymbol}
                    onChange={(e) => handleSearchChange(e.target.value)}
                    onFocus={() => searchSuggestions.length > 0 && setShowSuggestions(true)}
                    placeholder="Search by symbol or company name (e.g., NVDA, Apple, Microsoft)"
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-violet-500"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        setShowSuggestions(false);
                        fetchProjections(searchSymbol);
                      } else if (e.key === 'Escape') {
                        setShowSuggestions(false);
                      }
                    }}
                  />
                  {searchLoading && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                      <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
                    </div>
                  )}
                </div>
                
                {/* Search Suggestions Dropdown */}
                {showSuggestions && searchSuggestions.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-slate-800 border border-slate-600/50 rounded-lg shadow-xl max-h-64 overflow-y-auto">
                    {searchSuggestions.map((result, idx) => (
                      <button
                        key={`${result.symbol}-${idx}`}
                        onClick={() => selectSymbol(result.symbol)}
                        className="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-slate-700/50 transition-colors border-b border-slate-700/50 last:border-b-0 text-left"
                      >
                        <span className="font-mono font-bold text-violet-400 w-16">{result.symbol}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white truncate">{result.name}</p>
                          <p className="text-xs text-slate-500">{result.exchange} · {result.type}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => { setShowSuggestions(false); fetchProjections(searchSymbol); }}
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

                {/* AI Pattern Predictions */}
                {patternPredictions.length > 0 && (
                  <div className="p-4 bg-gradient-to-br from-violet-500/10 to-blue-500/10 rounded-lg border border-violet-500/30">
                    <div className="flex items-center gap-2 mb-4">
                      <Brain className="w-5 h-5 text-violet-400" />
                      <span className="text-sm font-bold text-white">AI Pattern Predictions</span>
                      <span className="text-xs text-slate-500">Detected patterns & signals</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {patternPredictions.map((pred, i) => (
                        <div 
                          key={i} 
                          className={`p-3 rounded-lg border ${
                            pred.type === 'bullish' 
                              ? 'bg-green-500/5 border-green-500/30' 
                              : pred.type === 'bearish'
                              ? 'bg-red-500/5 border-red-500/30'
                              : 'bg-slate-700/30 border-slate-600/30'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {pred.type === 'bullish' ? (
                                <TrendingUp className="w-4 h-4 text-green-400" />
                              ) : pred.type === 'bearish' ? (
                                <TrendingDown className="w-4 h-4 text-red-400" />
                              ) : (
                                <Activity className="w-4 h-4 text-slate-400" />
                              )}
                              <span className={`text-sm font-medium ${
                                pred.type === 'bullish' ? 'text-green-400' :
                                pred.type === 'bearish' ? 'text-red-400' : 'text-slate-300'
                              }`}>
                                {pred.pattern}
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              <div className={`h-2 w-16 bg-slate-700 rounded-full overflow-hidden`}>
                                <div 
                                  className={`h-full rounded-full ${
                                    pred.confidence >= 70 ? 'bg-green-500' :
                                    pred.confidence >= 50 ? 'bg-yellow-500' : 'bg-orange-500'
                                  }`}
                                  style={{ width: `${pred.confidence}%` }}
                                />
                              </div>
                              <span className="text-xs text-slate-400 w-10 text-right">{pred.confidence.toFixed(0)}%</span>
                            </div>
                          </div>
                          
                          {/* Mini Fluctuation Pattern SVG */}
                          <div className="my-2">
                            <svg viewBox="0 0 120 30" className="w-full h-8">
                              {/* Generate a fluctuating pattern based on prediction type */}
                              {pred.type === 'bullish' ? (
                                <>
                                  <path
                                    d="M0,20 Q10,22 20,18 T40,14 T60,12 T80,8 T100,6 T120,4"
                                    fill="none"
                                    stroke="rgba(34, 197, 94, 0.5)"
                                    strokeWidth="2"
                                  />
                                  <path
                                    d="M0,25 Q10,23 20,24 T40,20 T60,18 T80,16 T100,12 T120,8"
                                    fill="none"
                                    stroke="rgba(34, 197, 94, 0.3)"
                                    strokeWidth="1"
                                    strokeDasharray="3,3"
                                  />
                                </>
                              ) : pred.type === 'bearish' ? (
                                <>
                                  <path
                                    d="M0,8 Q10,10 20,12 T40,16 T60,18 T80,22 T100,24 T120,26"
                                    fill="none"
                                    stroke="rgba(239, 68, 68, 0.5)"
                                    strokeWidth="2"
                                  />
                                  <path
                                    d="M0,5 Q10,8 20,10 T40,12 T60,15 T80,18 T100,22 T120,24"
                                    fill="none"
                                    stroke="rgba(239, 68, 68, 0.3)"
                                    strokeWidth="1"
                                    strokeDasharray="3,3"
                                  />
                                </>
                              ) : (
                                <>
                                  <path
                                    d="M0,15 Q15,10 30,18 T60,14 T90,16 T120,15"
                                    fill="none"
                                    stroke="rgba(156, 163, 175, 0.5)"
                                    strokeWidth="2"
                                  />
                                  <path
                                    d="M0,15 Q20,20 40,12 T80,18 T120,15"
                                    fill="none"
                                    stroke="rgba(156, 163, 175, 0.3)"
                                    strokeWidth="1"
                                    strokeDasharray="3,3"
                                  />
                                </>
                              )}
                              {/* Current price marker */}
                              <circle 
                                cx="0" 
                                cy={pred.type === 'bullish' ? 20 : pred.type === 'bearish' ? 8 : 15} 
                                r="3" 
                                fill="white" 
                              />
                              {/* Target marker */}
                              {pred.target_price && (
                                <circle 
                                  cx="120" 
                                  cy={pred.type === 'bullish' ? 4 : pred.type === 'bearish' ? 26 : 15} 
                                  r="3" 
                                  fill={pred.type === 'bullish' ? '#22c55e' : pred.type === 'bearish' ? '#ef4444' : '#9ca3af'} 
                                />
                              )}
                            </svg>
                          </div>
                          
                          <p className="text-xs text-slate-400 mb-2">{pred.description}</p>
                          <div className="flex flex-wrap items-center gap-2 text-xs">
                            <span className="px-2 py-0.5 bg-slate-800/50 rounded text-slate-500">
                              ⏱ {pred.timeframe}
                            </span>
                            {pred.target_price && (
                              <span className="px-2 py-0.5 bg-green-500/10 rounded text-green-400">
                                🎯 ${pred.target_price.toFixed(2)}
                              </span>
                            )}
                            {pred.stop_loss && (
                              <span className="px-2 py-0.5 bg-red-500/10 rounded text-red-400">
                                🛑 ${pred.stop_loss.toFixed(2)}
                              </span>
                            )}
                          </div>
                          <div className="mt-2 pt-2 border-t border-slate-700/50">
                            <span className="text-xs text-slate-500">Trigger: </span>
                            <span className="text-xs text-slate-400">{pred.trigger}</span>
                          </div>
                        </div>
                      ))}
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
                          {/* Overall Formula */}
                          <div className="p-3 bg-violet-500/10 rounded-lg border border-violet-500/30 mb-4">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-xs font-medium text-violet-400 uppercase">Final Score Formula</span>
                            </div>
                            <code className="text-xs text-cyan-400 font-mono block">
                              Speculation_Score = (Social × 0.20) + (Sentiment × 0.15) + (Catalyst × 0.25) + (Technical × 0.15) + (Momentum × 0.15) + (Squeeze × 0.10)
                            </code>
                            <p className="text-xs text-slate-500 mt-2">
                              = ({analysisData.score_breakdown[0]?.value.toFixed(0)} × 0.20) + ({analysisData.score_breakdown[1]?.value.toFixed(0)} × 0.15) + ({analysisData.score_breakdown[2]?.value.toFixed(0)} × 0.25) + ({analysisData.score_breakdown[3]?.value.toFixed(0)} × 0.15) + ({analysisData.score_breakdown[4]?.value.toFixed(0)} × 0.15) + ({analysisData.score_breakdown[5]?.value.toFixed(0)} × 0.10)
                              = <span className="text-white font-bold">{analysisData.speculation_score.toFixed(1)}</span>
                            </p>
                          </div>
                          
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
                                  <span className="text-xs text-green-400">
                                    = {score.contribution.toFixed(1)}
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
                              
                              {/* Formula */}
                              {score.formula && (
                                <div className="p-2 bg-slate-800/50 rounded border border-slate-700/50 mb-2">
                                  <span className="text-xs text-slate-500">Formula: </span>
                                  <code className="text-xs text-cyan-400 font-mono">{score.formula}</code>
                                </div>
                              )}
                              
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
