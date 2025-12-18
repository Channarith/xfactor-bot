import React, { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';

interface ForexPair {
  symbol: string;
  base_currency: string;
  quote_currency: string;
  pair_type: string;
  pip_value: number;
  typical_spread_pips: number;
  avg_daily_range_pips: number;
}

interface Session {
  name: string;
  timezone: string;
  volatility: string;
  major_pairs: string[];
}

interface CurrentSession {
  active_sessions: Session[];
  overlaps: any[];
  recommendation: string;
  is_weekend: boolean;
}

interface CurrencyStrength {
  currency: string;
  strength: number;
  rank: number;
  trend: string;
}

interface EconomicEvent {
  id: string;
  title: string;
  currency: string;
  impact: string;
  datetime_utc: string;
}

const ForexPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'pairs' | 'sessions' | 'strength' | 'calendar'>('sessions');
  const [pairs, setPairs] = useState<ForexPair[]>([]);
  const [currentSession, setCurrentSession] = useState<CurrentSession | null>(null);
  const [currencyStrength, setCurrencyStrength] = useState<CurrencyStrength[]>([]);
  const [economicEvents, setEconomicEvents] = useState<EconomicEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [pairFilter, setPairFilter] = useState<string>('major');

  // Pip Calculator State
  const [pipCalc, setPipCalc] = useState({
    pair: 'EUR/USD',
    entryPrice: '',
    exitPrice: '',
    units: '10000',
  });
  const [pipResult, setPipResult] = useState<any>(null);

  useEffect(() => {
    fetchForexData();
  }, []);

  const fetchForexData = async () => {
    setLoading(true);
    try {
      const [pairsRes, sessionsRes, strengthRes, calendarRes] = await Promise.all([
        fetch(apiUrl('/api/forex/pairs')),
        fetch(apiUrl('/api/forex/sessions')),
        fetch(apiUrl('/api/forex/currency-strength')),
        fetch(apiUrl('/api/forex/calendar/high-impact?hours=72')),
      ]);

      if (pairsRes.ok) {
        const data = await pairsRes.json();
        setPairs(data.pairs || []);
      }
      if (sessionsRes.ok) {
        const data = await sessionsRes.json();
        setCurrentSession(data);
      }
      if (strengthRes.ok) {
        const data = await strengthRes.json();
        setCurrencyStrength(data.strengths || []);
      }
      if (calendarRes.ok) {
        const data = await calendarRes.json();
        setEconomicEvents(data.high_impact_events || []);
      }
    } catch (error) {
      console.error('Error fetching forex data:', error);
    }
    setLoading(false);
  };

  const calculatePips = async () => {
    if (!pipCalc.entryPrice || !pipCalc.exitPrice) return;
    try {
      const res = await fetch(apiUrl('/api/forex/calculate-pips'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pair: pipCalc.pair,
          entry_price: parseFloat(pipCalc.entryPrice),
          exit_price: parseFloat(pipCalc.exitPrice),
          units: parseInt(pipCalc.units),
          is_long: parseFloat(pipCalc.exitPrice) > parseFloat(pipCalc.entryPrice),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPipResult(data);
      }
    } catch (error) {
      console.error('Error calculating pips:', error);
    }
  };

  const getStrengthColor = (strength: number) => {
    if (strength >= 70) return 'text-green-400';
    if (strength >= 50) return 'text-yellow-400';
    if (strength >= 30) return 'text-orange-400';
    return 'text-red-400';
  };

  const getStrengthBg = (strength: number) => {
    if (strength >= 70) return 'bg-green-500';
    if (strength >= 50) return 'bg-yellow-500';
    if (strength >= 30) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getImpactBadge = (impact: string) => {
    const colors: Record<string, string> = {
      high: 'bg-red-500/20 text-red-400 border-red-500/30',
      medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      low: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    };
    return colors[impact] || colors.low;
  };

  const getSessionIcon = (name: string) => {
    const icons: Record<string, string> = {
      sydney: '🇦🇺',
      tokyo: '🇯🇵',
      london: '🇬🇧',
      new_york: '🇺🇸',
    };
    return icons[name] || '🌐';
  };

  const filteredPairs = pairs.filter(p => 
    pairFilter === 'all' || p.pair_type === pairFilter
  );

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          💱 Forex Trading
        </h2>
        <button
          onClick={fetchForexData}
          className="px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors text-sm"
        >
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto">
        {[
          { id: 'sessions', label: '🕐 Sessions' },
          { id: 'strength', label: '💪 Strength' },
          { id: 'pairs', label: '💹 Pairs' },
          { id: 'calendar', label: '📅 Calendar' },
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
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <>
          {/* Sessions Tab */}
          {activeTab === 'sessions' && currentSession && (
            <div className="space-y-6">
              {/* Current Status */}
              <div className={`p-4 rounded-lg ${currentSession.is_weekend ? 'bg-red-500/10 border border-red-500/30' : 'bg-green-500/10 border border-green-500/30'}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`w-3 h-3 rounded-full ${currentSession.is_weekend ? 'bg-red-500' : 'bg-green-500'} animate-pulse`}></span>
                  <span className={`font-medium ${currentSession.is_weekend ? 'text-red-400' : 'text-green-400'}`}>
                    {currentSession.is_weekend ? 'Markets Closed (Weekend)' : 'Markets Open'}
                  </span>
                </div>
                <p className="text-sm text-slate-300">{currentSession.recommendation}</p>
              </div>

              {/* Active Sessions */}
              <div>
                <h3 className="text-sm font-semibold text-slate-400 mb-3">Active Sessions</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {currentSession.active_sessions.length === 0 ? (
                    <p className="text-slate-400 col-span-2 text-center py-4">No active sessions</p>
                  ) : (
                    currentSession.active_sessions.map((session) => (
                      <div key={session.name} className="p-4 bg-slate-700/30 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-2xl">{getSessionIcon(session.name)}</span>
                          <span className="font-bold text-white capitalize">{session.name.replace('_', ' ')}</span>
                          <span className={`px-2 py-0.5 text-xs rounded-full ${
                            session.volatility === 'high' ? 'bg-red-500/20 text-red-400' :
                            session.volatility === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                            'bg-green-500/20 text-green-400'
                          }`}>
                            {session.volatility} volatility
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {session.major_pairs.map((pair) => (
                            <span key={pair} className="px-2 py-0.5 text-xs bg-slate-600/50 text-slate-300 rounded">
                              {pair}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Overlaps */}
              {currentSession.overlaps.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-400 mb-3">🔥 Session Overlaps (High Volatility)</h3>
                  {currentSession.overlaps.map((overlap, i) => (
                    <div key={i} className="p-3 bg-gradient-to-r from-orange-500/20 to-red-500/20 rounded-lg border border-orange-500/30">
                      <p className="text-white font-medium">{overlap.description}</p>
                      <div className="flex gap-1 mt-2">
                        {overlap.best_pairs?.map((pair: string) => (
                          <span key={pair} className="px-2 py-0.5 text-xs bg-orange-500/30 text-orange-300 rounded">
                            {pair}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Currency Strength Tab */}
          {activeTab === 'strength' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-slate-400">Currency Strength Meter</h3>
              <div className="space-y-2">
                {currencyStrength.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No strength data available. Add forex data to calculate.</p>
                ) : (
                  currencyStrength.map((currency) => (
                    <div key={currency.currency} className="flex items-center gap-3 p-3 bg-slate-700/30 rounded-lg">
                      <span className="text-sm font-bold text-white w-10">#{currency.rank}</span>
                      <span className="font-bold text-white w-12">{currency.currency}</span>
                      <div className="flex-1 h-4 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${getStrengthBg(currency.strength)}`}
                          style={{ width: `${currency.strength}%` }}
                        />
                      </div>
                      <span className={`font-bold w-12 text-right ${getStrengthColor(currency.strength)}`}>
                        {currency.strength.toFixed(0)}
                      </span>
                      <span className={`px-2 py-0.5 text-xs rounded-full ${
                        currency.trend === 'very_strong' || currency.trend === 'strong' ? 'bg-green-500/20 text-green-400' :
                        currency.trend === 'very_weak' || currency.trend === 'weak' ? 'bg-red-500/20 text-red-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {currency.trend.replace('_', ' ')}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Pairs Tab */}
          {activeTab === 'pairs' && (
            <div className="space-y-4">
              {/* Filter */}
              <div className="flex gap-2">
                {['major', 'minor', 'exotic', 'commodity', 'all'].map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setPairFilter(filter)}
                    className={`px-3 py-1.5 rounded-lg text-sm ${
                      pairFilter === filter ? 'bg-blue-600 text-white' : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    {filter.charAt(0).toUpperCase() + filter.slice(1)}
                  </button>
                ))}
              </div>

              {/* Pip Calculator */}
              <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-600/50">
                <h4 className="text-sm font-semibold text-slate-400 mb-3">Pip Calculator</h4>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <select
                    value={pipCalc.pair}
                    onChange={(e) => setPipCalc({ ...pipCalc, pair: e.target.value })}
                    className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm"
                  >
                    {pairs.slice(0, 20).map((p) => (
                      <option key={p.symbol} value={p.symbol}>{p.symbol}</option>
                    ))}
                  </select>
                  <input
                    type="number"
                    placeholder="Entry Price"
                    value={pipCalc.entryPrice}
                    onChange={(e) => setPipCalc({ ...pipCalc, entryPrice: e.target.value })}
                    className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm"
                    step="0.0001"
                  />
                  <input
                    type="number"
                    placeholder="Exit Price"
                    value={pipCalc.exitPrice}
                    onChange={(e) => setPipCalc({ ...pipCalc, exitPrice: e.target.value })}
                    className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm"
                    step="0.0001"
                  />
                  <input
                    type="number"
                    placeholder="Units"
                    value={pipCalc.units}
                    onChange={(e) => setPipCalc({ ...pipCalc, units: e.target.value })}
                    className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm"
                  />
                  <button
                    onClick={calculatePips}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                  >
                    Calculate
                  </button>
                </div>
                {pipResult && (
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="text-center p-2 bg-slate-800/50 rounded">
                      <div className={`text-xl font-bold ${pipResult.profit_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {pipResult.pips_moved?.toFixed(1)} pips
                      </div>
                      <div className="text-xs text-slate-400">Pip Movement</div>
                    </div>
                    <div className="text-center p-2 bg-slate-800/50 rounded">
                      <div className={`text-xl font-bold ${pipResult.profit_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${pipResult.profit_loss?.toFixed(2)}
                      </div>
                      <div className="text-xs text-slate-400">P/L</div>
                    </div>
                    <div className="text-center p-2 bg-slate-800/50 rounded">
                      <div className="text-xl font-bold text-blue-400">${pipResult.pip_value?.toFixed(4)}</div>
                      <div className="text-xs text-slate-400">Pip Value</div>
                    </div>
                  </div>
                )}
              </div>

              {/* Pairs List */}
              <div className="max-h-[300px] overflow-y-auto space-y-1">
                {filteredPairs.map((pair) => (
                  <div key={pair.symbol} className="flex items-center justify-between p-2 bg-slate-700/30 rounded-lg hover:bg-slate-700/50">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-white">{pair.symbol}</span>
                      <span className={`px-2 py-0.5 text-xs rounded ${
                        pair.pair_type === 'major' ? 'bg-blue-500/20 text-blue-400' :
                        pair.pair_type === 'minor' ? 'bg-purple-500/20 text-purple-400' :
                        pair.pair_type === 'exotic' ? 'bg-orange-500/20 text-orange-400' :
                        'bg-green-500/20 text-green-400'
                      }`}>
                        {pair.pair_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-slate-400">
                      <span>Spread: {pair.typical_spread_pips} pips</span>
                      <span>Range: {pair.avg_daily_range_pips} pips</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Economic Calendar Tab */}
          {activeTab === 'calendar' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-slate-400">High-Impact Events (Next 72 Hours)</h3>
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {economicEvents.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No high-impact events in the next 72 hours</p>
                ) : (
                  economicEvents.map((event) => (
                    <div key={event.id} className="p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">{event.currency}</span>
                          <span className={`px-2 py-0.5 text-xs rounded-full border ${getImpactBadge(event.impact)}`}>
                            {event.impact}
                          </span>
                        </div>
                        <span className="text-sm text-slate-400">
                          {new Date(event.datetime_utc).toLocaleDateString()} {new Date(event.datetime_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-sm text-slate-300">{event.title}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ForexPanel;

