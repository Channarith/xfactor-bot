import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, LineData, Time, CandlestickData, SeriesMarker } from 'lightweight-charts';
import { apiUrl } from '../config/api';
import { Search, TrendingUp, TrendingDown, Target, AlertTriangle, ChevronDown, ChevronUp, Layers, Activity, Users, DollarSign, BarChart3, Crosshair, PieChart, TrendingUp as TrendUp, Building2, Percent } from 'lucide-react';

// Types
interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface FundamentalDataPoint {
  date: string;
  value: number;
}

interface InflectionPoint {
  date: string;
  price: number;
  type: 'peak' | 'trough' | 'crossover_up' | 'crossover_down';
  magnitude: number;
  description: string;
}

interface EarningsEvent {
  date: string;
  reported_eps: number | null;
  estimated_eps: number | null;
  surprise_pct: number | null;
}

interface AnalystEstimate {
  date: string;
  estimate_type: string;
  low: number;
  mean: number;
  high: number;
  num_analysts: number;
}

interface CompanyMetrics {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  current_price: number;
  market_cap: number;
  pe_ratio: number | null;
  forward_pe: number | null;
  peg_ratio: number | null;
  price_to_book: number | null;
  profit_margin: number | null;
  roe: number | null;
  debt_to_equity: number | null;
  beta: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  dividend_yield: number | null;
  employees: number | null;
}

interface StockAnalysisData {
  symbol: string;
  company: CompanyMetrics;
  price_history: PricePoint[];
  pe_ratio_history: FundamentalDataPoint[];
  eps_history: FundamentalDataPoint[];
  market_cap_history: FundamentalDataPoint[];
  revenue_history: FundamentalDataPoint[];
  profit_margin_history: FundamentalDataPoint[];
  employee_count_history: FundamentalDataPoint[];
  sma_20: FundamentalDataPoint[];
  sma_50: FundamentalDataPoint[];
  sma_100: FundamentalDataPoint[];
  sma_200: FundamentalDataPoint[];
  ema_12: FundamentalDataPoint[];
  ema_26: FundamentalDataPoint[];
  rsi_14: FundamentalDataPoint[];
  volume_sma_20: FundamentalDataPoint[];
  earnings_history: EarningsEvent[];
  dividend_history: { date: string; amount: number }[];
  inflection_points: InflectionPoint[];
  analyst_estimates: AnalystEstimate[];
  price_targets: { low: number; mean: number; high: number; current: number };
  target_analysis: {
    trend: string;
    momentum: string;
    confidence: string;
    assessment: string;
    upside_to_mean_pct: number;
    likely_to_meet_target: boolean;
    estimated_days_to_mean_target: number | null;
  };
}

interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

// Overlay configuration
interface OverlayConfig {
  id: string;
  label: string;
  color: string;
  enabled: boolean;
  category: 'technical' | 'fundamental' | 'volume';
  icon: React.ReactNode;
}

const StockAnalyzer: React.FC = () => {
  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<StockAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState('2y');
  const [showInflections, setShowInflections] = useState(true);
  const [showProjections, setShowProjections] = useState(true);
  const [expandedSection, setExpandedSection] = useState<string | null>('chart');

  // Overlay states
  const [overlays, setOverlays] = useState<OverlayConfig[]>([
    // Technical overlays (same price scale)
    { id: 'sma_20', label: 'SMA 20', color: '#3b82f6', enabled: true, category: 'technical', icon: <Activity className="w-3 h-3" /> },
    { id: 'sma_50', label: 'SMA 50', color: '#8b5cf6', enabled: true, category: 'technical', icon: <Activity className="w-3 h-3" /> },
    { id: 'sma_100', label: 'SMA 100', color: '#14b8a6', enabled: false, category: 'technical', icon: <Activity className="w-3 h-3" /> },
    { id: 'sma_200', label: 'SMA 200', color: '#f59e0b', enabled: false, category: 'technical', icon: <Activity className="w-3 h-3" /> },
    { id: 'ema_12', label: 'EMA 12', color: '#10b981', enabled: false, category: 'technical', icon: <Activity className="w-3 h-3" /> },
    { id: 'ema_26', label: 'EMA 26', color: '#ef4444', enabled: false, category: 'technical', icon: <Activity className="w-3 h-3" /> },
    // Volume overlays
    { id: 'volume', label: 'Volume', color: '#64748b', enabled: true, category: 'volume', icon: <BarChart3 className="w-3 h-3" /> },
    { id: 'volume_sma', label: 'Vol SMA 20', color: '#94a3b8', enabled: false, category: 'volume', icon: <BarChart3 className="w-3 h-3" /> },
    // Fundamental overlays (secondary axis)
    { id: 'market_cap', label: 'Mkt Cap ($B)', color: '#06b6d4', enabled: false, category: 'fundamental', icon: <Building2 className="w-3 h-3" /> },
    { id: 'pe_ratio', label: 'P/E Ratio', color: '#f97316', enabled: false, category: 'fundamental', icon: <PieChart className="w-3 h-3" /> },
    { id: 'profit_margin', label: 'Profit Margin %', color: '#84cc16', enabled: false, category: 'fundamental', icon: <Percent className="w-3 h-3" /> },
    { id: 'revenue', label: 'Revenue ($B)', color: '#a855f7', enabled: false, category: 'fundamental', icon: <DollarSign className="w-3 h-3" /> },
    { id: 'eps', label: 'EPS', color: '#ec4899', enabled: false, category: 'fundamental', icon: <TrendUp className="w-3 h-3" /> },
  ]);

  // Chart refs
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const overlaySeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Search stocks
  const searchStocks = useCallback(async (query: string) => {
    if (query.length < 1) {
      setSearchResults([]);
      return;
    }

    try {
      const res = await fetch(apiUrl(`/api/symbols/search?q=${encodeURIComponent(query)}&limit=10`));
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
        setShowSearchResults(true);
      }
    } catch (e) {
      console.error('Search error:', e);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = setTimeout(() => {
      searchStocks(searchQuery);
    }, 300);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchQuery, searchStocks]);

  // Fetch stock analysis
  const fetchAnalysis = useCallback(async (symbol: string) => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(apiUrl(`/api/stock-analysis/analyze/${symbol}?period=${period}`));
      if (res.ok) {
        const data = await res.json();
        setAnalysisData(data);
        setSelectedSymbol(symbol);
      } else {
        const errData = await res.json();
        setError(errData.detail || 'Failed to analyze stock');
      }
    } catch (e) {
      setError('Network error. Please try again.');
      console.error('Analysis error:', e);
    } finally {
      setLoading(false);
    }
  }, [period]);

  // Toggle overlay
  const toggleOverlay = useCallback((id: string) => {
    setOverlays(prev => prev.map(o => 
      o.id === id ? { ...o, enabled: !o.enabled } : o
    ));
  }, []);

  // Create and update chart
  useEffect(() => {
    if (!chartContainerRef.current || !analysisData || analysisData.price_history.length === 0) {
      return;
    }

    // Cleanup existing chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      overlaySeriesRef.current.clear();
    }

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
        fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.03)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        scaleMargins: { top: 0.1, bottom: 0.25 },
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: 1,
        vertLine: { color: 'rgba(139, 92, 246, 0.4)', width: 1, style: 2 },
        horzLine: { color: 'rgba(139, 92, 246, 0.4)', width: 1, style: 2 },
      },
    });

    chartRef.current = chart;

    // Create candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });
    candleSeriesRef.current = candleSeries;

    // Set candlestick data
    const candleData: CandlestickData[] = analysisData.price_history.map(p => ({
      time: p.date as Time,
      open: p.open,
      high: p.high,
      low: p.low,
      close: p.close,
    }));
    candleSeries.setData(candleData);

    // Add volume histogram if enabled
    const volumeOverlay = overlays.find(o => o.id === 'volume');
    if (volumeOverlay?.enabled) {
      const volumeSeries = chart.addHistogramSeries({
        color: '#64748b',
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      });
      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.85, bottom: 0 },
      });
      volumeSeries.setData(
        analysisData.price_history.map(p => ({
          time: p.date as Time,
          value: p.volume,
          color: p.close >= p.open ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)',
        }))
      );
      volumeSeriesRef.current = volumeSeries;
    }

    // Add overlay series
    const overlayDataMap: Record<string, FundamentalDataPoint[]> = {
      sma_20: analysisData.sma_20,
      sma_50: analysisData.sma_50,
      sma_100: analysisData.sma_100,
      sma_200: analysisData.sma_200,
      ema_12: analysisData.ema_12,
      ema_26: analysisData.ema_26,
    };

    overlays.filter(o => o.enabled && o.category === 'technical').forEach(overlay => {
      const data = overlayDataMap[overlay.id];
      if (data && data.length > 0) {
        const lineSeries = chart.addLineSeries({
          color: overlay.color,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        lineSeries.setData(
          data.map(d => ({ time: d.date as Time, value: d.value }))
        );
        overlaySeriesRef.current.set(overlay.id, lineSeries);
      }
    });

    // Add fundamental overlays on secondary axis (left side)
    const fundamentalDataMap: Record<string, FundamentalDataPoint[]> = {
      market_cap: analysisData.market_cap_history || [],
      pe_ratio: analysisData.pe_ratio_history || [],
      profit_margin: analysisData.profit_margin_history || [],
      revenue: analysisData.revenue_history || [],
      eps: analysisData.eps_history || [],
    };

    overlays.filter(o => o.enabled && o.category === 'fundamental').forEach(overlay => {
      const data = fundamentalDataMap[overlay.id];
      if (data && data.length > 0) {
        // Create a separate price scale for each fundamental
        const scaleId = `fundamental_${overlay.id}`;
        const lineSeries = chart.addLineSeries({
          color: overlay.color,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          crosshairMarkerVisible: true,
          priceScaleId: scaleId,
          lineStyle: 0, // Solid
        });
        
        // Configure the secondary price scale (will appear on left)
        chart.priceScale(scaleId).applyOptions({
          scaleMargins: { top: 0.1, bottom: 0.3 },
          borderColor: overlay.color,
          visible: true,
        });
        
        lineSeries.setData(
          data.map(d => ({ time: d.date as Time, value: d.value }))
        );
        overlaySeriesRef.current.set(overlay.id, lineSeries);
      }
    });

    // Add inflection point markers
    if (showInflections && analysisData.inflection_points.length > 0) {
      const markers: SeriesMarker<Time>[] = analysisData.inflection_points.map(ip => {
        let shape: 'arrowUp' | 'arrowDown' | 'circle' = 'circle';
        let color = '#8b5cf6';
        let position: 'aboveBar' | 'belowBar' = 'aboveBar';
        
        if (ip.type === 'peak' || ip.type === 'crossover_down') {
          shape = 'arrowDown';
          color = '#ef4444';
          position = 'aboveBar';
        } else if (ip.type === 'trough' || ip.type === 'crossover_up') {
          shape = 'arrowUp';
          color = '#22c55e';
          position = 'belowBar';
        }

        return {
          time: ip.date as Time,
          position,
          color,
          shape,
          text: ip.type === 'crossover_up' ? 'GC' : ip.type === 'crossover_down' ? 'DC' : '',
          size: 1,
        };
      });
      candleSeries.setMarkers(markers);
    }

    // Add price target lines if showing projections
    if (showProjections && analysisData.price_targets) {
      const { low, mean, high } = analysisData.price_targets;
      
      if (mean > 0) {
        const targetLine = chart.addLineSeries({
          color: '#3b82f6',
          lineWidth: 1,
          lineStyle: 2, // Dashed
          priceLineVisible: false,
          lastValueVisible: true,
          crosshairMarkerVisible: false,
        });
        // Extend into future
        const lastDate = analysisData.price_history[analysisData.price_history.length - 1].date;
        const futureDate = new Date(lastDate);
        futureDate.setMonth(futureDate.getMonth() + 6);
        targetLine.setData([
          { time: lastDate as Time, value: mean },
          { time: futureDate.toISOString().split('T')[0] as Time, value: mean },
        ]);
      }

      if (high > 0 && high !== mean) {
        const highLine = chart.addLineSeries({
          color: '#22c55e',
          lineWidth: 1,
          lineStyle: 3, // Dotted
          priceLineVisible: false,
          lastValueVisible: false,
        });
        const lastDate = analysisData.price_history[analysisData.price_history.length - 1].date;
        const futureDate = new Date(lastDate);
        futureDate.setMonth(futureDate.getMonth() + 6);
        highLine.setData([
          { time: lastDate as Time, value: high },
          { time: futureDate.toISOString().split('T')[0] as Time, value: high },
        ]);
      }

      if (low > 0 && low !== mean) {
        const lowLine = chart.addLineSeries({
          color: '#ef4444',
          lineWidth: 1,
          lineStyle: 3,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        const lastDate = analysisData.price_history[analysisData.price_history.length - 1].date;
        const futureDate = new Date(lastDate);
        futureDate.setMonth(futureDate.getMonth() + 6);
        lowLine.setData([
          { time: lastDate as Time, value: low },
          { time: futureDate.toISOString().split('T')[0] as Time, value: low },
        ]);
      }
    }

    chart.timeScale().fitContent();

    // Handle resize
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
  }, [analysisData, overlays, showInflections, showProjections]);

  // Format large numbers
  const formatNumber = (num: number | null | undefined, prefix = '') => {
    if (num === null || num === undefined) return 'N/A';
    if (num >= 1e12) return `${prefix}${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `${prefix}${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `${prefix}${(num / 1e6).toFixed(2)}M`;
    if (num >= 1e3) return `${prefix}${(num / 1e3).toFixed(2)}K`;
    return `${prefix}${num.toFixed(2)}`;
  };

  const formatPercent = (num: number | null | undefined) => {
    if (num === null || num === undefined) return 'N/A';
    return `${(num * 100).toFixed(2)}%`;
  };

  return (
    <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50 bg-gradient-to-r from-violet-500/10 to-blue-500/10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Crosshair className="w-5 h-5 text-violet-400" />
            Stock Analyzer
          </h2>
          {selectedSymbol && (
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-white">${selectedSymbol}</span>
              {analysisData?.company && (
                <span className="text-sm text-slate-400">{analysisData.company.name}</span>
              )}
            </div>
          )}
        </div>

        {/* Search */}
        <div className="relative">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
                onFocus={() => searchResults.length > 0 && setShowSearchResults(true)}
                placeholder="Search stocks (e.g., AAPL, NVDA, TSLA)"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-800/80 border border-slate-600/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30"
              />
            </div>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="px-3 py-2 bg-slate-800/80 border border-slate-600/50 rounded-lg text-white focus:outline-none focus:border-violet-500/50"
            >
              <option value="1mo">1 Month</option>
              <option value="3mo">3 Months</option>
              <option value="6mo">6 Months</option>
              <option value="1y">1 Year</option>
              <option value="2y">2 Years</option>
              <option value="5y">5 Years</option>
            </select>
            <button
              onClick={() => searchQuery && fetchAnalysis(searchQuery)}
              disabled={loading || !searchQuery}
              className="px-6 py-2 bg-violet-600 hover:bg-violet-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'Analyze'
              )}
            </button>
          </div>

          {/* Search Results Dropdown */}
          {showSearchResults && searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-600/50 rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto">
              {searchResults.map((result) => (
                <button
                  key={result.symbol}
                  onClick={() => {
                    setSearchQuery(result.symbol);
                    setShowSearchResults(false);
                    fetchAnalysis(result.symbol);
                  }}
                  className="w-full px-4 py-2.5 text-left hover:bg-slate-700/50 transition-colors flex items-center justify-between"
                >
                  <div>
                    <span className="font-bold text-white">{result.symbol}</span>
                    <span className="text-slate-400 ml-2 text-sm">{result.name}</span>
                  </div>
                  <span className="text-xs text-slate-500">{result.exchange}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border-b border-red-500/30">
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-4 h-4" />
            {error}
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="p-12 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
            <span className="text-slate-400 text-sm">Analyzing {searchQuery}...</span>
          </div>
        </div>
      )}

      {/* Analysis Content */}
      {!loading && analysisData && (
        <>
          {/* Quick Stats Bar */}
          <div className="p-4 bg-slate-800/30 border-b border-slate-700/50 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">${analysisData.company.current_price.toFixed(2)}</div>
              <div className="text-xs text-slate-500">Current Price</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-blue-400">{formatNumber(analysisData.company.market_cap, '$')}</div>
              <div className="text-xs text-slate-500">Market Cap</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-white">{analysisData.company.pe_ratio?.toFixed(2) || 'N/A'}</div>
              <div className="text-xs text-slate-500">P/E Ratio</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-white">{analysisData.company.peg_ratio?.toFixed(2) || 'N/A'}</div>
              <div className="text-xs text-slate-500">PEG Ratio</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-green-400">{formatPercent(analysisData.company.profit_margin)}</div>
              <div className="text-xs text-slate-500">Profit Margin</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-yellow-400">{analysisData.company.beta?.toFixed(2) || 'N/A'}</div>
              <div className="text-xs text-slate-500">Beta</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-violet-400">{formatPercent(analysisData.company.dividend_yield)}</div>
              <div className="text-xs text-slate-500">Div Yield</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-cyan-400">{formatNumber(analysisData.company.employees)}</div>
              <div className="text-xs text-slate-500">Employees</div>
            </div>
          </div>

          {/* Overlay Controls */}
          <div className="p-3 bg-slate-800/20 border-b border-slate-700/50">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-500 font-medium mr-2 flex items-center gap-1">
                <Layers className="w-3 h-3" /> OVERLAYS:
              </span>
              {overlays.map((overlay) => (
                <button
                  key={overlay.id}
                  onClick={() => toggleOverlay(overlay.id)}
                  className={`px-2.5 py-1 text-xs rounded-md flex items-center gap-1.5 transition-all ${
                    overlay.enabled
                      ? 'bg-slate-700 text-white border border-slate-600'
                      : 'bg-slate-800/50 text-slate-500 border border-slate-700/50 hover:border-slate-600'
                  }`}
                  style={{ borderLeftColor: overlay.enabled ? overlay.color : undefined, borderLeftWidth: overlay.enabled ? 3 : 1 }}
                >
                  {overlay.icon}
                  {overlay.label}
                </button>
              ))}
              <div className="h-4 w-px bg-slate-700 mx-2" />
              <button
                onClick={() => setShowInflections(!showInflections)}
                className={`px-2.5 py-1 text-xs rounded-md flex items-center gap-1.5 transition-all ${
                  showInflections
                    ? 'bg-violet-600/30 text-violet-300 border border-violet-500/50'
                    : 'bg-slate-800/50 text-slate-500 border border-slate-700/50 hover:border-slate-600'
                }`}
              >
                <Target className="w-3 h-3" />
                Inflections ({analysisData.inflection_points.length})
              </button>
              <button
                onClick={() => setShowProjections(!showProjections)}
                className={`px-2.5 py-1 text-xs rounded-md flex items-center gap-1.5 transition-all ${
                  showProjections
                    ? 'bg-blue-600/30 text-blue-300 border border-blue-500/50'
                    : 'bg-slate-800/50 text-slate-500 border border-slate-700/50 hover:border-slate-600'
                }`}
              >
                <TrendingUp className="w-3 h-3" />
                Price Targets
              </button>
            </div>
          </div>

          {/* Chart */}
          <div className="p-4">
            <div ref={chartContainerRef} className="rounded-lg overflow-hidden bg-slate-900/50" />
          </div>

          {/* Target Analysis Panel */}
          {analysisData.target_analysis && analysisData.price_targets.mean > 0 && (
            <div className="p-4 border-t border-slate-700/50 bg-gradient-to-r from-blue-500/5 to-violet-500/5">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <Target className="w-4 h-4 text-blue-400" />
                    Target Meeting Analysis
                  </h3>
                  <p className="text-sm text-slate-400 mt-1">Will this stock meet analyst price targets?</p>
                </div>
                <div className={`px-3 py-1.5 rounded-full text-sm font-medium ${
                  analysisData.target_analysis.confidence === 'high' 
                    ? 'bg-green-500/20 text-green-400'
                    : analysisData.target_analysis.confidence === 'medium'
                    ? 'bg-yellow-500/20 text-yellow-400'
                    : 'bg-red-500/20 text-red-400'
                }`}>
                  {analysisData.target_analysis.confidence?.toUpperCase()} CONFIDENCE
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="p-3 bg-slate-800/50 rounded-lg">
                  <div className="text-xs text-slate-500 mb-1">Mean Target</div>
                  <div className="text-xl font-bold text-blue-400">${analysisData.price_targets.mean.toFixed(2)}</div>
                  <div className={`text-sm ${analysisData.target_analysis.upside_to_mean_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {analysisData.target_analysis.upside_to_mean_pct > 0 ? '+' : ''}{analysisData.target_analysis.upside_to_mean_pct?.toFixed(1)}%
                  </div>
                </div>
                <div className="p-3 bg-slate-800/50 rounded-lg">
                  <div className="text-xs text-slate-500 mb-1">Low Target</div>
                  <div className="text-xl font-bold text-red-400">${analysisData.price_targets.low.toFixed(2)}</div>
                </div>
                <div className="p-3 bg-slate-800/50 rounded-lg">
                  <div className="text-xs text-slate-500 mb-1">High Target</div>
                  <div className="text-xl font-bold text-green-400">${analysisData.price_targets.high.toFixed(2)}</div>
                </div>
                <div className="p-3 bg-slate-800/50 rounded-lg">
                  <div className="text-xs text-slate-500 mb-1">Trend</div>
                  <div className={`text-xl font-bold flex items-center gap-1 ${
                    analysisData.target_analysis.trend === 'bullish' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {analysisData.target_analysis.trend === 'bullish' ? (
                      <TrendingUp className="w-5 h-5" />
                    ) : (
                      <TrendingDown className="w-5 h-5" />
                    )}
                    {analysisData.target_analysis.trend?.toUpperCase()}
                  </div>
                </div>
              </div>

              <div className="p-3 bg-slate-800/30 rounded-lg">
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-full ${
                    analysisData.target_analysis.likely_to_meet_target
                      ? 'bg-green-500/20'
                      : 'bg-amber-500/20'
                  }`}>
                    {analysisData.target_analysis.likely_to_meet_target ? (
                      <TrendingUp className="w-5 h-5 text-green-400" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-amber-400" />
                    )}
                  </div>
                  <div>
                    <p className="text-white font-medium">{analysisData.target_analysis.assessment}</p>
                    {analysisData.target_analysis.estimated_days_to_mean_target && (
                      <p className="text-sm text-slate-400 mt-1">
                        At current momentum, estimated {analysisData.target_analysis.estimated_days_to_mean_target} days to reach mean target
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Inflection Points List */}
          {showInflections && analysisData.inflection_points.length > 0 && (
            <div className="p-4 border-t border-slate-700/50">
              <button
                onClick={() => setExpandedSection(expandedSection === 'inflections' ? null : 'inflections')}
                className="w-full flex items-center justify-between text-left"
              >
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-violet-400" />
                  Inflection Points
                  <span className="text-sm text-slate-500 font-normal">
                    ({analysisData.inflection_points.length} detected)
                  </span>
                </h3>
                {expandedSection === 'inflections' ? (
                  <ChevronUp className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                )}
              </button>

              {expandedSection === 'inflections' && (
                <div className="mt-4 space-y-2 max-h-64 overflow-y-auto">
                  {analysisData.inflection_points.slice().reverse().map((ip, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-lg flex items-center justify-between ${
                        ip.type === 'peak' || ip.type === 'crossover_down'
                          ? 'bg-red-500/10 border border-red-500/20'
                          : 'bg-green-500/10 border border-green-500/20'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-full ${
                          ip.type === 'peak' || ip.type === 'crossover_down'
                            ? 'bg-red-500/20'
                            : 'bg-green-500/20'
                        }`}>
                          {ip.type === 'peak' || ip.type === 'crossover_down' ? (
                            <TrendingDown className={`w-4 h-4 ${ip.type === 'peak' || ip.type === 'crossover_down' ? 'text-red-400' : 'text-green-400'}`} />
                          ) : (
                            <TrendingUp className="w-4 h-4 text-green-400" />
                          )}
                        </div>
                        <div>
                          <div className="text-sm font-medium text-white">{ip.description}</div>
                          <div className="text-xs text-slate-500">{ip.date}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium text-white">${ip.price.toFixed(2)}</div>
                        {ip.magnitude !== 0 && (
                          <div className={`text-xs ${ip.magnitude > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {ip.magnitude > 0 ? '+' : ''}{ip.magnitude.toFixed(1)}%
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Earnings History */}
          {analysisData.earnings_history.length > 0 && (
            <div className="p-4 border-t border-slate-700/50">
              <button
                onClick={() => setExpandedSection(expandedSection === 'earnings' ? null : 'earnings')}
                className="w-full flex items-center justify-between text-left"
              >
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-green-400" />
                  Earnings History
                </h3>
                {expandedSection === 'earnings' ? (
                  <ChevronUp className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                )}
              </button>

              {expandedSection === 'earnings' && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-slate-500 text-left">
                        <th className="pb-2 font-medium">Date</th>
                        <th className="pb-2 font-medium">Reported EPS</th>
                        <th className="pb-2 font-medium">Estimated EPS</th>
                        <th className="pb-2 font-medium">Surprise</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysisData.earnings_history.slice(0, 8).map((e, i) => (
                        <tr key={i} className="border-t border-slate-700/50">
                          <td className="py-2 text-white">{e.date}</td>
                          <td className="py-2 text-white">{e.reported_eps?.toFixed(2) || 'N/A'}</td>
                          <td className="py-2 text-slate-400">{e.estimated_eps?.toFixed(2) || 'N/A'}</td>
                          <td className={`py-2 ${
                            e.surprise_pct && e.surprise_pct > 0 ? 'text-green-400' : 
                            e.surprise_pct && e.surprise_pct < 0 ? 'text-red-400' : 'text-slate-400'
                          }`}>
                            {e.surprise_pct ? `${e.surprise_pct > 0 ? '+' : ''}${e.surprise_pct.toFixed(1)}%` : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Future Estimates */}
          {analysisData.analyst_estimates.length > 0 && (
            <div className="p-4 border-t border-slate-700/50">
              <button
                onClick={() => setExpandedSection(expandedSection === 'estimates' ? null : 'estimates')}
                className="w-full flex items-center justify-between text-left"
              >
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Target className="w-4 h-4 text-blue-400" />
                  Future Estimates
                </h3>
                {expandedSection === 'estimates' ? (
                  <ChevronUp className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                )}
              </button>

              {expandedSection === 'estimates' && (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                  {analysisData.analyst_estimates.map((est, i) => (
                    <div key={i} className="p-3 bg-slate-800/50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-slate-400">{est.date}</span>
                        <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">
                          {est.estimate_type.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="text-center">
                          <div className="text-xs text-slate-500">Low</div>
                          <div className="text-sm text-red-400">${est.low.toFixed(2)}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-slate-500">Mean</div>
                          <div className="text-lg font-bold text-white">${est.mean.toFixed(2)}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-slate-500">High</div>
                          <div className="text-sm text-green-400">${est.high.toFixed(2)}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Company Info */}
          <div className="p-4 border-t border-slate-700/50 bg-slate-800/20">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-slate-500">Sector</div>
                <div className="text-white font-medium">{analysisData.company.sector || 'N/A'}</div>
              </div>
              <div>
                <div className="text-slate-500">Industry</div>
                <div className="text-white font-medium">{analysisData.company.industry || 'N/A'}</div>
              </div>
              <div>
                <div className="text-slate-500">52W High</div>
                <div className="text-white font-medium">${analysisData.company.fifty_two_week_high?.toFixed(2) || 'N/A'}</div>
              </div>
              <div>
                <div className="text-slate-500">52W Low</div>
                <div className="text-white font-medium">${analysisData.company.fifty_two_week_low?.toFixed(2) || 'N/A'}</div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Empty State */}
      {!loading && !analysisData && !error && (
        <div className="p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800/50 flex items-center justify-center">
            <Search className="w-8 h-8 text-slate-600" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">Search for a stock to analyze</h3>
          <p className="text-slate-500 text-sm max-w-md mx-auto">
            Enter a stock symbol to see comprehensive analysis including price charts, 
            technical indicators, fundamental metrics, inflection points, and future projections.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {['AAPL', 'NVDA', 'MSFT', 'TSLA', 'GOOGL', 'AMZN'].map(symbol => (
              <button
                key={symbol}
                onClick={() => {
                  setSearchQuery(symbol);
                  fetchAnalysis(symbol);
                }}
                className="px-3 py-1.5 bg-slate-800/50 hover:bg-slate-700 text-slate-400 hover:text-white rounded-md text-sm transition-colors"
              >
                {symbol}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StockAnalyzer;

