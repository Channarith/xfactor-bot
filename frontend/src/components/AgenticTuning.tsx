import { useState, useEffect } from 'react';
import { 
  Zap, 
  Brain, 
  Target, 
  TrendingUp, 
  Clock, 
  Trophy, 
  Trash2, 
  Play, 
  Square,
  Settings,
  BarChart3,
  Cpu,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Sparkles
} from 'lucide-react';
import { getApiBaseUrl } from '../config/api';

interface TuningStatus {
  enabled: boolean;
  running: boolean;
  started_at: string | null;
  days_running: number;
  current_phase: string;
  target: string;
  total_bots: number;
  active_bots: number;
  pruned_bots: number;
  champions: string[];
  gpu_usage: {
    active: number;
    total: number;
    usage_pct: number;
  };
  compute_savings_pct: number;
  next_phase_in_days: number;
}

interface BotRanking {
  bot_id: string;
  bot_name: string;
  final_score: number;
  rank: number;
  total_profit: number;
  win_rate: number;
  is_champion: boolean;
  is_active: boolean;
}

interface OptimizationTarget {
  id: string;
  name: string;
  description: string;
  primary_weight: string;
}

const PHASE_COLORS: Record<string, string> = {
  initial_blast: 'text-blue-400 bg-blue-500/20 border-blue-500/30',
  first_pruning: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30',
  deep_pruning: 'text-orange-400 bg-orange-500/20 border-orange-500/30',
  optimal_state: 'text-green-400 bg-green-500/20 border-green-500/30',
  maintenance: 'text-purple-400 bg-purple-500/20 border-purple-500/30',
};

const PHASE_LABELS: Record<string, string> = {
  initial_blast: '🚀 Initial Blast',
  first_pruning: '✂️ First Pruning',
  deep_pruning: '🔪 Deep Pruning',
  optimal_state: '🏆 Optimal State',
  maintenance: '🔄 Maintenance',
};

export function AgenticTuning() {
  const [status, setStatus] = useState<TuningStatus | null>(null);
  const [rankings, setRankings] = useState<BotRanking[]>([]);
  const [targets, setTargets] = useState<OptimizationTarget[]>([]);
  const [selectedTarget, setSelectedTarget] = useState('max_profit');
  const [autoPrune, setAutoPrune] = useState(true);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showRankings, setShowRankings] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/agentic-tuning/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (e) {
      console.error('Failed to fetch tuning status:', e);
    }
  };

  const fetchRankings = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/agentic-tuning/rankings`);
      if (res.ok) {
        const data = await res.json();
        setRankings(data.rankings || []);
      }
    } catch (e) {
      console.error('Failed to fetch rankings:', e);
    }
  };

  const fetchTargets = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/agentic-tuning/targets`);
      if (res.ok) {
        const data = await res.json();
        setTargets(data.targets || []);
      }
    } catch (e) {
      console.error('Failed to fetch targets:', e);
    }
  };

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await Promise.all([fetchStatus(), fetchRankings(), fetchTargets()]);
      setLoading(false);
    };
    loadAll();

    // Refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setStarting(true);
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/agentic-tuning/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: selectedTarget,
          auto_prune: autoPrune,
        }),
      });
      if (res.ok) {
        await fetchStatus();
        await fetchRankings();
      }
    } catch (e) {
      console.error('Failed to start tuning:', e);
    }
    setStarting(false);
  };

  const handleStop = async () => {
    setStopping(true);
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/agentic-tuning/stop`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchStatus();
      }
    } catch (e) {
      console.error('Failed to stop tuning:', e);
    }
    setStopping(false);
  };

  const handleForceEvaluation = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/agentic-tuning/force-evaluation`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchRankings();
      }
    } catch (e) {
      console.error('Failed to force evaluation:', e);
    }
  };

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card">
      {/* Header */}
      <div className="p-4 border-b border-border bg-gradient-to-r from-purple-500/10 to-blue-500/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/20">
              <Brain className="h-6 w-6 text-purple-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                Agentic Tuning
                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
                  ATRWAC
                </span>
              </h2>
              <p className="text-sm text-muted-foreground">
                Automatically prune underperforming bots to maximize efficiency
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {status?.running ? (
              <button
                onClick={handleStop}
                disabled={stopping}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors"
              >
                <Square className="h-4 w-4" />
                {stopping ? 'Stopping...' : 'Stop'}
              </button>
            ) : (
              <button
                onClick={handleStart}
                disabled={starting}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 transition-colors"
              >
                <Play className="h-4 w-4" />
                {starting ? 'Starting...' : 'Start Tuning'}
              </button>
            )}
            
            <button
              onClick={() => setShowSettings(!showSettings)}
              className={`p-2 rounded-lg border transition-colors ${
                showSettings 
                  ? 'bg-primary/20 text-primary border-primary/30' 
                  : 'bg-secondary/50 text-muted-foreground border-border hover:border-primary/50'
              }`}
            >
              <Settings className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="p-4 border-b border-border bg-secondary/30">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Target Selection */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Optimization Target
              </label>
              <select
                value={selectedTarget}
                onChange={(e) => setSelectedTarget(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {targets.map((target) => (
                  <option key={target.id} value={target.id}>
                    {target.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground mt-1">
                {targets.find(t => t.id === selectedTarget)?.description}
              </p>
            </div>

            {/* Auto Prune Toggle */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Auto-Prune
              </label>
              <button
                onClick={() => setAutoPrune(!autoPrune)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                  autoPrune
                    ? 'bg-green-500/20 text-green-400 border-green-500/30'
                    : 'bg-secondary/50 text-muted-foreground border-border'
                }`}
              >
                {autoPrune ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    Enabled - Auto prune underperformers
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4" />
                    Disabled - Manual pruning only
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Status Cards */}
      {status && (
        <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Phase */}
          <div className="p-3 rounded-lg border border-border bg-secondary/30">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Clock className="h-4 w-4" />
              Phase
            </div>
            <div className={`text-lg font-bold px-2 py-1 rounded border ${PHASE_COLORS[status.current_phase] || 'text-foreground'}`}>
              {PHASE_LABELS[status.current_phase] || status.current_phase}
            </div>
            {status.next_phase_in_days > 0 && (
              <p className="text-xs text-muted-foreground mt-1">
                Next phase in {status.next_phase_in_days} days
              </p>
            )}
          </div>

          {/* Active Bots */}
          <div className="p-3 rounded-lg border border-border bg-secondary/30">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Activity className="h-4 w-4" />
              Active Bots
            </div>
            <div className="text-2xl font-bold text-foreground">
              {status.active_bots}
              <span className="text-sm text-muted-foreground font-normal">
                /{status.total_bots}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {status.pruned_bots} pruned
            </p>
          </div>

          {/* Champions */}
          <div className="p-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10">
            <div className="flex items-center gap-2 text-sm text-yellow-400 mb-1">
              <Trophy className="h-4 w-4" />
              Champions
            </div>
            <div className="text-2xl font-bold text-yellow-400">
              {status.champions.length}
            </div>
            <p className="text-xs text-yellow-400/70">
              Top performers
            </p>
          </div>

          {/* Compute Savings */}
          <div className="p-3 rounded-lg border border-green-500/30 bg-green-500/10">
            <div className="flex items-center gap-2 text-sm text-green-400 mb-1">
              <Cpu className="h-4 w-4" />
              Compute Saved
            </div>
            <div className="text-2xl font-bold text-green-400">
              {status.compute_savings_pct.toFixed(0)}%
            </div>
            <p className="text-xs text-green-400/70">
              {status.gpu_usage.active}/{status.gpu_usage.total} GPUs active
            </p>
          </div>
        </div>
      )}

      {/* Rankings Section */}
      <div className="border-t border-border">
        <button
          onClick={() => setShowRankings(!showRankings)}
          className="w-full p-4 flex items-center justify-between hover:bg-secondary/30 transition-colors"
        >
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-muted-foreground" />
            <span className="font-medium text-foreground">Bot Rankings</span>
            <span className="text-sm text-muted-foreground">
              ({rankings.length} bots)
            </span>
          </div>
          {showRankings ? (
            <ChevronUp className="h-5 w-5 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-5 w-5 text-muted-foreground" />
          )}
        </button>

        {showRankings && (
          <div className="p-4 pt-0">
            <div className="flex justify-end mb-2">
              <button
                onClick={handleForceEvaluation}
                className="text-sm px-3 py-1 rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors"
              >
                <Zap className="h-3 w-3 inline mr-1" />
                Force Evaluation
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-border">
                    <th className="pb-2 pr-4">Rank</th>
                    <th className="pb-2 pr-4">Bot</th>
                    <th className="pb-2 pr-4">Score</th>
                    <th className="pb-2 pr-4">Profit</th>
                    <th className="pb-2 pr-4">Win Rate</th>
                    <th className="pb-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rankings.slice(0, 10).map((bot) => (
                    <tr key={bot.bot_id} className="border-b border-border/50">
                      <td className="py-2 pr-4">
                        {bot.rank <= 3 ? (
                          <span className="text-lg">
                            {bot.rank === 1 ? '🥇' : bot.rank === 2 ? '🥈' : '🥉'}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">#{bot.rank}</span>
                        )}
                      </td>
                      <td className="py-2 pr-4 font-medium text-foreground">
                        {bot.bot_name}
                      </td>
                      <td className="py-2 pr-4">
                        <span className="font-mono text-primary">
                          {bot.final_score.toFixed(0)}
                        </span>
                      </td>
                      <td className={`py-2 pr-4 ${bot.total_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${bot.total_profit.toFixed(2)}
                      </td>
                      <td className="py-2 pr-4">
                        {(bot.win_rate * 100).toFixed(1)}%
                      </td>
                      <td className="py-2">
                        {bot.is_champion ? (
                          <span className="flex items-center gap-1 text-yellow-400">
                            <Sparkles className="h-3 w-3" />
                            Champion
                          </span>
                        ) : bot.is_active ? (
                          <span className="text-green-400">Active</span>
                        ) : (
                          <span className="text-red-400">Pruned</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {rankings.length > 10 && (
                <p className="text-sm text-muted-foreground text-center mt-2">
                  Showing top 10 of {rankings.length} bots
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Target Description */}
      {status?.running && (
        <div className="p-4 border-t border-border bg-secondary/20">
          <div className="flex items-center gap-2 text-sm">
            <Target className="h-4 w-4 text-primary" />
            <span className="text-muted-foreground">Optimizing for:</span>
            <span className="font-medium text-primary">
              {targets.find(t => t.id === status.target)?.name || status.target}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default AgenticTuning;

