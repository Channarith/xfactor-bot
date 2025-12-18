import React, { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';

interface RiskScore {
  bot_id: string;
  bot_name: string;
  overall_risk_score: number;
  risk_level: string;
  risk_level_color: string;
  component_scores: {
    position_size: number;
    concentration: number;
    drawdown: number;
    volatility: number;
    leverage: number;
    correlation: number;
    win_rate: number;
    exposure: number;
  };
  metrics: {
    risk_adjusted_ratios: {
      sharpe_ratio: number;
      sortino_ratio: number;
      calmar_ratio: number;
    };
    win_loss: {
      win_rate_pct: number;
      profit_factor: number;
    };
    drawdown: {
      current_pct: number;
      max_pct: number;
    };
  };
  alerts: any[];
  recommendations: string[];
}

interface RiskAlert {
  id: string;
  category: string;
  level: string;
  title: string;
  description: string;
  recommendation: string;
  bot_id: string;
}

const BotRiskPanel: React.FC = () => {
  const [riskScores, setRiskScores] = useState<RiskScore[]>([]);
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [selectedBot, setSelectedBot] = useState<RiskScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [portfolioRisk, setPortfolioRisk] = useState<any>(null);

  useEffect(() => {
    fetchRiskData();
  }, []);

  const fetchRiskData = async () => {
    setLoading(true);
    try {
      const [scoresRes, alertsRes, portfolioRes] = await Promise.all([
        fetch(apiUrl('/api/bots/risk/all')),
        fetch(apiUrl('/api/bots/risk/alerts')),
        fetch(apiUrl('/api/bots/risk/portfolio')),
      ]);

      if (scoresRes.ok) {
        const data = await scoresRes.json();
        setRiskScores(data.scores || []);
      }
      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data.alerts || []);
      }
      if (portfolioRes.ok) {
        const data = await portfolioRes.json();
        setPortfolioRisk(data);
      }
    } catch (error) {
      console.error('Error fetching risk data:', error);
    }
    setLoading(false);
  };

  const calculateBotRisk = async (botId: string) => {
    try {
      const res = await fetch(apiUrl(`/api/bots/risk/${botId}/score`));
      if (res.ok) {
        const data = await res.json();
        setSelectedBot(data);
        // Refresh all scores
        fetchRiskData();
      }
    } catch (error) {
      console.error('Error calculating risk:', error);
    }
  };

  const getRiskColor = (level: string) => {
    const colors: Record<string, string> = {
      critical: 'text-red-400 bg-red-500/20',
      high: 'text-orange-400 bg-orange-500/20',
      elevated: 'text-yellow-400 bg-yellow-500/20',
      moderate: 'text-green-400 bg-green-500/20',
      low: 'text-cyan-400 bg-cyan-500/20',
    };
    return colors[level] || colors.moderate;
  };

  const getRiskBgColor = (score: number) => {
    if (score >= 80) return 'from-red-500/30 to-red-600/30';
    if (score >= 60) return 'from-orange-500/30 to-orange-600/30';
    if (score >= 40) return 'from-yellow-500/30 to-yellow-600/30';
    if (score >= 20) return 'from-green-500/30 to-green-600/30';
    return 'from-cyan-500/30 to-cyan-600/30';
  };

  const ComponentScoreBar = ({ label, score }: { label: string; score: number }) => (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400 w-24">{label}</span>
      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${
            score >= 70 ? 'bg-red-500' :
            score >= 50 ? 'bg-orange-500' :
            score >= 30 ? 'bg-yellow-500' :
            'bg-green-500'
          }`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs text-slate-300 w-8 text-right">{score.toFixed(0)}</span>
    </div>
  );

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          🛡️ Bot Risk Management
        </h2>
        <button
          onClick={fetchRiskData}
          className="px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors text-sm"
        >
          Refresh
        </button>
      </div>

      {/* Portfolio Risk Overview */}
      {portfolioRisk && (
        <div className={`mb-6 p-4 rounded-lg bg-gradient-to-r ${getRiskBgColor(portfolioRisk.overall_risk_score)} border border-slate-600/50`}>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center">
              <div className="text-3xl font-bold text-white">{portfolioRisk.overall_risk_score?.toFixed(0) || 0}</div>
              <div className="text-xs text-slate-400">Portfolio Risk</div>
            </div>
            <div className="text-center">
              <div className={`text-lg font-bold ${getRiskColor(portfolioRisk.risk_level).split(' ')[0]}`}>
                {portfolioRisk.risk_level?.toUpperCase() || 'N/A'}
              </div>
              <div className="text-xs text-slate-400">Risk Level</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-white">{portfolioRisk.bot_count || 0}</div>
              <div className="text-xs text-slate-400">Bots Monitored</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-orange-400">{portfolioRisk.high_risk_bots || 0}</div>
              <div className="text-xs text-slate-400">High Risk Bots</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-red-400">{portfolioRisk.critical_alerts || 0}</div>
              <div className="text-xs text-slate-400">Critical Alerts</div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bot Risk Scores */}
        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-400 mb-3">Bot Risk Scores</h3>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
              </div>
            ) : riskScores.length === 0 ? (
              <p className="text-slate-400 text-center py-8">No risk scores calculated yet.</p>
            ) : (
              riskScores.map((score) => (
                <div
                  key={score.bot_id}
                  onClick={() => setSelectedBot(score)}
                  className={`p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer ${
                    selectedBot?.bot_id === score.bot_id ? 'ring-2 ring-blue-500' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-12 h-12 rounded-lg flex items-center justify-center text-xl font-bold text-white"
                        style={{ backgroundColor: score.risk_level_color + '40' }}
                      >
                        {score.overall_risk_score.toFixed(0)}
                      </div>
                      <div>
                        <p className="text-white font-medium">{score.bot_name}</p>
                        <span className={`px-2 py-0.5 text-xs rounded-full ${getRiskColor(score.risk_level)}`}>
                          {score.risk_level}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-400">Sharpe:</span>
                        <span className={score.metrics?.risk_adjusted_ratios?.sharpe_ratio >= 1 ? 'text-green-400' : 'text-yellow-400'}>
                          {score.metrics?.risk_adjusted_ratios?.sharpe_ratio?.toFixed(2) || 'N/A'}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500">
                        {score.alerts?.length || 0} alerts
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Selected Bot Details or Alerts */}
        <div>
          {selectedBot ? (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-400">Risk Breakdown</h3>
                <button onClick={() => setSelectedBot(null)} className="text-slate-400 hover:text-white text-sm">✕</button>
              </div>
              <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-600/50">
                <h4 className="text-white font-medium mb-4">{selectedBot.bot_name}</h4>
                
                <div className="space-y-3 mb-4">
                  <ComponentScoreBar label="Position Size" score={selectedBot.component_scores.position_size} />
                  <ComponentScoreBar label="Concentration" score={selectedBot.component_scores.concentration} />
                  <ComponentScoreBar label="Drawdown" score={selectedBot.component_scores.drawdown} />
                  <ComponentScoreBar label="Volatility" score={selectedBot.component_scores.volatility} />
                  <ComponentScoreBar label="Leverage" score={selectedBot.component_scores.leverage} />
                  <ComponentScoreBar label="Correlation" score={selectedBot.component_scores.correlation} />
                  <ComponentScoreBar label="Win Rate" score={selectedBot.component_scores.win_rate} />
                  <ComponentScoreBar label="Exposure" score={selectedBot.component_scores.exposure} />
                </div>

                <div className="grid grid-cols-2 gap-2 mb-4">
                  <div className="p-2 bg-slate-800/50 rounded text-center">
                    <div className="text-lg font-bold text-white">{selectedBot.metrics?.win_loss?.win_rate_pct?.toFixed(0) || 0}%</div>
                    <div className="text-xs text-slate-400">Win Rate</div>
                  </div>
                  <div className="p-2 bg-slate-800/50 rounded text-center">
                    <div className="text-lg font-bold text-red-400">{selectedBot.metrics?.drawdown?.max_pct?.toFixed(1) || 0}%</div>
                    <div className="text-xs text-slate-400">Max DD</div>
                  </div>
                </div>

                {selectedBot.recommendations?.length > 0 && (
                  <div>
                    <h5 className="text-xs font-semibold text-slate-400 mb-2">Recommendations</h5>
                    <ul className="space-y-1">
                      {selectedBot.recommendations.slice(0, 3).map((rec, i) => (
                        <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                          <span className="text-blue-400">•</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div>
              <h3 className="text-sm font-semibold text-slate-400 mb-3">Recent Alerts</h3>
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {alerts.length === 0 ? (
                  <p className="text-slate-400 text-center py-4 text-sm">No active alerts</p>
                ) : (
                  alerts.slice(0, 10).map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-3 rounded-lg border ${
                        alert.level === 'critical' ? 'bg-red-500/10 border-red-500/30' :
                        alert.level === 'high' ? 'bg-orange-500/10 border-orange-500/30' :
                        'bg-yellow-500/10 border-yellow-500/30'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${getRiskColor(alert.level)}`}>
                          {alert.level.toUpperCase()}
                        </span>
                        <span className="text-xs text-slate-400">{alert.category}</span>
                      </div>
                      <p className="text-sm text-white">{alert.title}</p>
                      <p className="text-xs text-slate-400 mt-1">{alert.description}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BotRiskPanel;

