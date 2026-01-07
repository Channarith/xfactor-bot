import { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  BarChart3, 
  RefreshCw, 
  AlertCircle,
  CheckCircle,
  XCircle,
  Bot,
  User,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Target
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:9876';

interface Trade {
  trade_id: string;
  timestamp: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  total_value: number;
  order_type: string;
  source: string;
  source_name: string;
  broker: string;
  pnl?: number;
  pnl_pct?: number;
  reasoning?: string;
}

interface PerformanceStats {
  count: number;
  trades_with_pnl: number;
  total_pnl: number;
  win_rate: number;
  avg_pnl: number;
  total_volume: number;
  winners: number;
  losers: number;
  best_trade: { symbol: string; pnl: number } | null;
  worst_trade: { symbol: string; pnl: number } | null;
}

interface Comparison {
  bot_trades: PerformanceStats;
  manual_trades: PerformanceStats;
  comparison: {
    pnl_difference: number;
    bots_outperform_by: number;
    manual_outperform_by: number;
    win_rate_difference: number;
    recommendation: string;
  };
}

export default function ManualTrading() {
  // Order form state
  const [symbol, setSymbol] = useState('');
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [quantity, setQuantity] = useState('');
  const [orderType, setOrderType] = useState('market');
  const [limitPrice, setLimitPrice] = useState('');
  const [note, setNote] = useState('');
  
  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastOrder, setLastOrder] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Data state
  const [trades, setTrades] = useState<Trade[]>([]);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [activeTab, setActiveTab] = useState<'trade' | 'history' | 'comparison'>('trade');
  const [historyFilter, setHistoryFilter] = useState<'all' | 'manual' | 'bot'>('all');
  
  // Load data
  useEffect(() => {
    fetchTrades();
    fetchComparison();
  }, [historyFilter]);
  
  const fetchTrades = async () => {
    try {
      const source = historyFilter === 'all' ? '' : `?source=${historyFilter}`;
      const res = await fetch(`${API_BASE}/api/trading/history${source}`);
      const data = await res.json();
      setTrades(data.trades || []);
    } catch (e) {
      console.error('Failed to fetch trades:', e);
    }
  };
  
  const fetchComparison = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/trading/performance/comparison?days=30`);
      const data = await res.json();
      setComparison(data);
    } catch (e) {
      console.error('Failed to fetch comparison:', e);
    }
  };
  
  const submitOrder = async () => {
    if (!symbol || !quantity) {
      setError('Symbol and quantity are required');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    setLastOrder(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/trading/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol.toUpperCase(),
          side,
          quantity: parseFloat(quantity),
          order_type: orderType,
          limit_price: orderType === 'limit' ? parseFloat(limitPrice) : null,
          note,
        }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Order failed');
      }
      
      setLastOrder(data);
      setSymbol('');
      setQuantity('');
      setNote('');
      fetchTrades();
      fetchComparison();
      
    } catch (e: any) {
      setError(e.message || 'Failed to submit order');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const formatCurrency = (value: number) => {
    const formatted = Math.abs(value).toLocaleString('en-US', { 
      style: 'currency', 
      currency: 'USD',
      minimumFractionDigits: 2 
    });
    return value >= 0 ? formatted : `-${formatted}`;
  };
  
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };
  
  return (
    <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-xl">
              <DollarSign className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Manual Trading</h2>
              <p className="text-xs text-slate-400">Execute trades & compare with bot performance</p>
            </div>
          </div>
          <button
            onClick={() => { fetchTrades(); fetchComparison(); }}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-slate-400" />
          </button>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-1 mt-4 bg-slate-800/50 p-1 rounded-lg">
          {(['trade', 'history', 'comparison'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all ${
                activeTab === tab
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab === 'trade' && '📝 Trade'}
              {tab === 'history' && '📜 History'}
              {tab === 'comparison' && '📊 Bot vs Manual'}
            </button>
          ))}
        </div>
      </div>
      
      <div className="p-4">
        {/* Trade Tab */}
        {activeTab === 'trade' && (
          <div className="space-y-4">
            {/* Buy/Sell Toggle */}
            <div className="flex gap-2">
              <button
                onClick={() => setSide('buy')}
                className={`flex-1 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all ${
                  side === 'buy'
                    ? 'bg-emerald-500/20 text-emerald-400 border-2 border-emerald-500/50'
                    : 'bg-slate-800/50 text-slate-400 border-2 border-transparent hover:border-slate-600'
                }`}
              >
                <TrendingUp className="w-5 h-5" />
                BUY
              </button>
              <button
                onClick={() => setSide('sell')}
                className={`flex-1 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all ${
                  side === 'sell'
                    ? 'bg-red-500/20 text-red-400 border-2 border-red-500/50'
                    : 'bg-slate-800/50 text-slate-400 border-2 border-transparent hover:border-slate-600'
                }`}
              >
                <TrendingDown className="w-5 h-5" />
                SELL
              </button>
            </div>
            
            {/* Symbol Input */}
            <div>
              <label className="block text-sm text-slate-400 mb-1">Symbol</label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="AAPL, TSLA, BTC-USD..."
                className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            
            {/* Quantity Input */}
            <div>
              <label className="block text-sm text-slate-400 mb-1">Quantity</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="Number of shares"
                className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            
            {/* Order Type */}
            <div>
              <label className="block text-sm text-slate-400 mb-1">Order Type</label>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value)}
                className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-xl text-white focus:outline-none focus:border-emerald-500/50"
              >
                <option value="market">Market</option>
                <option value="limit">Limit</option>
                <option value="stop">Stop</option>
              </select>
            </div>
            
            {/* Limit Price (conditional) */}
            {orderType === 'limit' && (
              <div>
                <label className="block text-sm text-slate-400 mb-1">Limit Price</label>
                <input
                  type="number"
                  value={limitPrice}
                  onChange={(e) => setLimitPrice(e.target.value)}
                  placeholder="$0.00"
                  className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
                />
              </div>
            )}
            
            {/* Note */}
            <div>
              <label className="block text-sm text-slate-400 mb-1">Note (optional)</label>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Why are you making this trade?"
                className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            
            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400">
                <AlertCircle className="w-5 h-5" />
                {error}
              </div>
            )}
            
            {/* Success */}
            {lastOrder && (
              <div className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400">
                <CheckCircle className="w-5 h-5" />
                <div>
                  <div className="font-medium">{lastOrder.message}</div>
                  <div className="text-xs opacity-80">
                    Order ID: {lastOrder.order?.order_id} | Broker: {lastOrder.broker}
                    {lastOrder.is_paper && <span className="ml-2 text-yellow-400">(Paper)</span>}
                  </div>
                </div>
              </div>
            )}
            
            {/* Submit Button */}
            <button
              onClick={submitOrder}
              disabled={isSubmitting || !symbol || !quantity}
              className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all ${
                side === 'buy'
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white'
                  : 'bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-400 hover:to-rose-400 text-white'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  {side === 'buy' ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                  {side.toUpperCase()} {symbol || 'SYMBOL'}
                </>
              )}
            </button>
          </div>
        )}
        
        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            {/* Filter */}
            <div className="flex gap-2">
              {(['all', 'manual', 'bot'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setHistoryFilter(filter)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                    historyFilter === filter
                      ? 'bg-slate-700 text-white'
                      : 'bg-slate-800/50 text-slate-400 hover:text-white'
                  }`}
                >
                  {filter === 'all' && <BarChart3 className="w-4 h-4" />}
                  {filter === 'manual' && <User className="w-4 h-4" />}
                  {filter === 'bot' && <Bot className="w-4 h-4" />}
                  {filter.charAt(0).toUpperCase() + filter.slice(1)}
                </button>
              ))}
            </div>
            
            {/* Trade List */}
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {trades.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  No trades recorded yet
                </div>
              ) : (
                trades.map((trade) => (
                  <div
                    key={trade.trade_id}
                    className="p-3 bg-slate-800/30 rounded-xl border border-slate-700/30 hover:border-slate-600/50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${
                          trade.side === 'buy' ? 'bg-emerald-500/20' : 'bg-red-500/20'
                        }`}>
                          {trade.side === 'buy' 
                            ? <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                            : <ArrowDownRight className="w-4 h-4 text-red-400" />
                          }
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white">{trade.symbol}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              trade.source === 'manual' 
                                ? 'bg-violet-500/20 text-violet-400' 
                                : 'bg-blue-500/20 text-blue-400'
                            }`}>
                              {trade.source === 'manual' ? '👤 Manual' : '🤖 Bot'}
                            </span>
                          </div>
                          <div className="text-xs text-slate-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatTime(trade.timestamp)}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`font-medium ${trade.side === 'buy' ? 'text-emerald-400' : 'text-red-400'}`}>
                          {trade.side.toUpperCase()} {trade.quantity}
                        </div>
                        <div className="text-xs text-slate-500">
                          @ ${trade.price.toFixed(2)}
                        </div>
                        {trade.pnl !== undefined && trade.pnl !== null && (
                          <div className={`text-xs font-medium ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {formatCurrency(trade.pnl)}
                          </div>
                        )}
                      </div>
                    </div>
                    {trade.reasoning && (
                      <div className="mt-2 text-xs text-slate-400 bg-slate-800/50 p-2 rounded-lg">
                        💭 {trade.reasoning}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
        
        {/* Comparison Tab */}
        {activeTab === 'comparison' && comparison && (
          <div className="space-y-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 gap-3">
              {/* Bot Stats */}
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <Bot className="w-5 h-5 text-blue-400" />
                  <span className="font-semibold text-blue-400">Bot Trades</span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400 text-sm">Total Trades</span>
                    <span className="text-white font-medium">{comparison.bot_trades.count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 text-sm">Win Rate</span>
                    <span className="text-white font-medium">{comparison.bot_trades.win_rate}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 text-sm">Total P&L</span>
                    <span className={`font-medium ${comparison.bot_trades.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {formatCurrency(comparison.bot_trades.total_pnl)}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Manual Stats */}
              <div className="p-4 bg-violet-500/10 border border-violet-500/30 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <User className="w-5 h-5 text-violet-400" />
                  <span className="font-semibold text-violet-400">Manual Trades</span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400 text-sm">Total Trades</span>
                    <span className="text-white font-medium">{comparison.manual_trades.count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 text-sm">Win Rate</span>
                    <span className="text-white font-medium">{comparison.manual_trades.win_rate}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 text-sm">Total P&L</span>
                    <span className={`font-medium ${comparison.manual_trades.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {formatCurrency(comparison.manual_trades.total_pnl)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Winner Badge */}
            <div className={`p-4 rounded-xl border ${
              comparison.comparison.pnl_difference > 0
                ? 'bg-blue-500/10 border-blue-500/30'
                : comparison.comparison.pnl_difference < 0
                ? 'bg-violet-500/10 border-violet-500/30'
                : 'bg-slate-800/50 border-slate-700/30'
            }`}>
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-xl ${
                  comparison.comparison.pnl_difference > 0
                    ? 'bg-blue-500/20'
                    : comparison.comparison.pnl_difference < 0
                    ? 'bg-violet-500/20'
                    : 'bg-slate-700/50'
                }`}>
                  {comparison.comparison.pnl_difference > 0 
                    ? <Bot className="w-6 h-6 text-blue-400" />
                    : comparison.comparison.pnl_difference < 0
                    ? <User className="w-6 h-6 text-violet-400" />
                    : <Target className="w-6 h-6 text-slate-400" />
                  }
                </div>
                <div>
                  <div className="font-semibold text-white">
                    {comparison.comparison.pnl_difference > 0
                      ? '🤖 Bots are winning!'
                      : comparison.comparison.pnl_difference < 0
                      ? '👤 You are winning!'
                      : '🤝 It\'s a tie!'}
                  </div>
                  <div className="text-sm text-slate-400">
                    {comparison.comparison.recommendation}
                  </div>
                </div>
              </div>
            </div>
            
            {/* Detailed Comparison */}
            <div className="p-4 bg-slate-800/30 rounded-xl space-y-3">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Detailed Comparison (Last 30 Days)
              </h3>
              
              <div className="grid grid-cols-3 gap-4 text-center text-sm">
                <div></div>
                <div className="text-blue-400 font-medium">🤖 Bots</div>
                <div className="text-violet-400 font-medium">👤 Manual</div>
                
                <div className="text-slate-400 text-left">Winners</div>
                <div className="text-emerald-400">{comparison.bot_trades.winners}</div>
                <div className="text-emerald-400">{comparison.manual_trades.winners}</div>
                
                <div className="text-slate-400 text-left">Losers</div>
                <div className="text-red-400">{comparison.bot_trades.losers}</div>
                <div className="text-red-400">{comparison.manual_trades.losers}</div>
                
                <div className="text-slate-400 text-left">Avg P&L</div>
                <div className={comparison.bot_trades.avg_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                  {formatCurrency(comparison.bot_trades.avg_pnl)}
                </div>
                <div className={comparison.manual_trades.avg_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                  {formatCurrency(comparison.manual_trades.avg_pnl)}
                </div>
                
                <div className="text-slate-400 text-left">Volume</div>
                <div className="text-white">{formatCurrency(comparison.bot_trades.total_volume)}</div>
                <div className="text-white">{formatCurrency(comparison.manual_trades.total_volume)}</div>
              </div>
              
              {/* Best/Worst Trades */}
              <div className="grid grid-cols-2 gap-4 pt-3 border-t border-slate-700/50">
                <div>
                  <div className="text-xs text-slate-500 mb-1">Best Bot Trade</div>
                  {comparison.bot_trades.best_trade ? (
                    <div className="text-emerald-400 text-sm">
                      {comparison.bot_trades.best_trade.symbol}: {formatCurrency(comparison.bot_trades.best_trade.pnl)}
                    </div>
                  ) : (
                    <div className="text-slate-500 text-sm">No trades yet</div>
                  )}
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">Best Manual Trade</div>
                  {comparison.manual_trades.best_trade ? (
                    <div className="text-emerald-400 text-sm">
                      {comparison.manual_trades.best_trade.symbol}: {formatCurrency(comparison.manual_trades.best_trade.pnl)}
                    </div>
                  ) : (
                    <div className="text-slate-500 text-sm">No trades yet</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'comparison' && !comparison && (
          <div className="text-center py-8 text-slate-500">
            Loading comparison data...
          </div>
        )}
      </div>
    </div>
  );
}

