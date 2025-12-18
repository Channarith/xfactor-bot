import { useState } from 'react';
import { X, HelpCircle, Zap, Bot, LineChart, Shield, Settings, Cpu, Globe, Calendar } from 'lucide-react';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const VERSION = '1.0.3';
const RELEASE_DATE = 'December 17, 2025';

const features = [
  {
    icon: Bot,
    title: '37+ Trading Bots',
    description: 'Pre-configured bots for stocks, options, futures, crypto, and commodities with customizable strategies.'
  },
  {
    icon: Zap,
    title: 'Multi-Broker Support',
    description: 'Connect to IBKR, Alpaca, Schwab, Tradier, and NinjaTrader 8 for futures. OAuth, API keys, or username/password.'
  },
  {
    icon: LineChart,
    title: 'Volatility-Adaptive Stops',
    description: 'ATR-based dynamic stop losses and take profits that automatically adjust to market volatility.'
  },
  {
    icon: Shield,
    title: 'Risk Management',
    description: 'Real-time VaR, max drawdown protection, Martingale sizing options, and VIX-based circuit breakers.'
  },
  {
    icon: Cpu,
    title: 'AI-Powered Analysis',
    description: 'Integration with OpenAI, Anthropic Claude, and local Ollama for market insights and strategy optimization.'
  },
  {
    icon: Calendar,
    title: 'Market Regime Detection',
    description: 'Automatic trend vs range detection with ADX, Bollinger squeeze, and trading recommendations.'
  },
  {
    icon: Settings,
    title: 'Strategy Templates & Builder',
    description: '10+ pre-built strategy templates plus visual drag-and-drop strategy builder for custom strategies.'
  },
  {
    icon: Globe,
    title: 'Social Trading & TradingView',
    description: 'Copy top traders, share strategies, and receive TradingView webhook alerts directly.'
  }
];

const quickStart = [
  { step: 1, title: 'Connect Broker', description: 'Go to Admin Panel > Broker Config and connect your trading account.' },
  { step: 2, title: 'Select Trading Mode', description: 'Choose Demo (simulated), Paper (broker paper trading), or Live mode.' },
  { step: 3, title: 'Configure Bots', description: 'Enable desired bots from the Bot Manager panel and customize their strategies.' },
  { step: 4, title: 'Set Risk Controls', description: 'Configure position limits, stop-losses, and daily loss limits in Risk Controls.' },
  { step: 5, title: 'Start Trading', description: 'Click Start on individual bots or use Start All to begin automated trading.' }
];

const changelog = [
  {
    version: '1.0.3',
    date: 'December 17, 2025',
    changes: [
      '🔮 AI-Powered Market Forecasting Engine',
      '📹 Video Platform Analysis (YouTube, TikTok, Instagram)',
      '🛡️ Bot Risk Management System (0-100 scoring)',
      'Track FinTok & YouTube finance influencers',
      'Viral content alerts across all platforms',
      'Risk-Adjusted Metrics: Sharpe, Sortino, VaR',
      'Social Sentiment (Twitter/X, Reddit, StockTwits)',
      'Speculation Scoring Algorithm',
      'Catalyst Tracker & AI Hypothesis Generator',
      '50+ Known Financial Influencer Database'
    ]
  },
  {
    version: '1.0.2',
    date: 'December 17, 2025',
    changes: [
      '🌍 Comprehensive Forex Trading',
      '60+ Currency Pairs with pip calculator',
      'Currency Strength Meter',
      'Economic Calendar',
      'MT5 & OANDA Integration'
    ]
  },
  {
    version: '1.0.1',
    date: 'December 17, 2025',
    changes: [
      '🎉 Quantvue-Inspired Features',
      'Volatility-Adaptive SL/TP with ATR-based dynamic stops',
      'TradingView Webhook Integration',
      'Market Regime Detection',
      'Martingale Position Sizing',
      'Strategy Templates Library (10+ strategies)',
      'NinjaTrader 8 Integration',
      'Visual Strategy Builder',
      'Social Trading Platform'
    ]
  },
  {
    version: '0.9.8',
    date: 'December 17, 2025',
    changes: [
      'Platform-specific fixes for Windows and Linux releases',
      'Exclude uvloop on Windows (Unix-only library)',
      'Enhanced zombie process cleanup with fallback commands',
      'Comprehensive debug logging for connection troubleshooting',
      'Fixed WebSocket connection loops (stable refs, no dependency loops)'
    ]
  },
  {
    version: '0.9.7',
    date: 'December 16, 2025',
    changes: [
      'Offline admin login - works even when backend is down',
      'Enhanced debug logging for "Failed to fetch bots" errors',
      'Fixed CSP to allow 127.0.0.1 connections in desktop app',
      'Improved API URL handling for Tauri desktop',
      'Added agentic tuning algorithm (ATRWAC) for bot optimization',
      'Zombie process cleanup scripts for macOS/Linux/Windows'
    ]
  },
  {
    version: '0.9.6',
    date: 'December 16, 2025',
    changes: [
      'Rebuilt x64 backend with all dependencies properly bundled',
      'Fixed Gatekeeper blocking on Intel Macs',
      'ChromeOS support via Linux .deb package',
      'Manual DMG creation fallback for reliable builds',
      'Version sync across all config files'
    ]
  },
  {
    version: '0.9.5',
    date: 'December 15, 2025',
    changes: [
      'Help popup with features, quick start, and changelog',
      'API-based LLM support (OpenAI, Anthropic, Ollama)',
      'Replaced pandas-ta with ta library for NumPy compatibility',
      'Cross-platform desktop builds (macOS ARM64/Intel, Windows, Linux)',
      'Added hypothesis testing framework'
    ]
  },
  {
    version: '0.9.4',
    date: 'December 13, 2025',
    changes: [
      'Fixed sidecar binary bundling for desktop app',
      'Backend auto-launch improvements'
    ]
  },
  {
    version: '0.9.3',
    date: 'December 13, 2025',
    changes: [
      'Auto-Tune UI for automatic strategy optimization',
      'Seasonal Events UI in Strategy Controls',
      'Enhanced bot details with Win Rate, Uptime, Error tracking'
    ]
  },
  {
    version: '0.9.0',
    date: 'December 12, 2025',
    changes: [
      'Desktop application with Tauri',
      'Multiple broker authentication methods',
      '37 pre-configured trading bots',
      'Global stock exchange support (40+ exchanges)'
    ]
  }
];

export default function HelpModal({ isOpen, onClose }: HelpModalProps) {
  const [activeTab, setActiveTab] = useState<'features' | 'quickstart' | 'changelog'>('features');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden border border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700 bg-gradient-to-r from-blue-600/20 to-purple-600/20">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <HelpCircle className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">XFactor Bot Help</h2>
              <p className="text-sm text-slate-400">Version {VERSION} • {RELEASE_DATE}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-700">
          {[
            { id: 'features', label: 'Features' },
            { id: 'quickstart', label: 'Quick Start' },
            { id: 'changelog', label: 'Changelog' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-500/10'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {activeTab === 'features' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {features.map((feature, index) => (
                <div
                  key={index}
                  className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-blue-500/50 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-blue-500/20 rounded-lg shrink-0">
                      <feature.icon className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white mb-1">{feature.title}</h3>
                      <p className="text-sm text-slate-400">{feature.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'quickstart' && (
            <div className="space-y-4">
              <p className="text-slate-300 mb-6">
                Get started with XFactor Bot in 5 simple steps:
              </p>
              {quickStart.map((item) => (
                <div
                  key={item.step}
                  className="flex items-start gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700"
                >
                  <div className="w-8 h-8 flex items-center justify-center bg-blue-500 rounded-full text-white font-bold shrink-0">
                    {item.step}
                  </div>
                  <div>
                    <h3 className="font-semibold text-white mb-1">{item.title}</h3>
                    <p className="text-sm text-slate-400">{item.description}</p>
                  </div>
                </div>
              ))}

              <div className="mt-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <h4 className="font-semibold text-amber-400 mb-2">⚠️ Important Notes</h4>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Always start with Paper trading mode to test strategies</li>
                  <li>• Set appropriate risk limits before enabling Live trading</li>
                  <li>• Monitor bot performance regularly using the Performance Charts</li>
                  <li>• Use Auto-Tune to optimize bot parameters automatically</li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'changelog' && (
            <div className="space-y-6">
              {changelog.map((release) => (
                <div key={release.version} className="border-l-2 border-blue-500 pl-4">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-sm font-mono rounded">
                      v{release.version}
                    </span>
                    <span className="text-sm text-slate-400">{release.date}</span>
                  </div>
                  <ul className="space-y-1">
                    {release.changes.map((change, i) => (
                      <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                        <span className="text-green-400 mt-1">•</span>
                        {change}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-700 bg-slate-800/50">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">
              © 2025 XFactor Trading • AI-Powered Automated Trading System
            </p>
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">
                {VERSION}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

