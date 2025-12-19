import React, { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';

interface VideoContent {
  id: string;
  platform: string;
  title: string;
  url: string;
  creator: {
    name: string;
    handle: string;
    followers: number;
    verified: boolean;
  };
  engagement: {
    views: number;
    likes: number;
    comments: number;
  };
  analysis: {
    symbols: string[];
    sentiment_score: number;
    viral_score: number;
  };
}

interface Influencer {
  name: string;
  handle: string;
  followers: number;
  focus: string[];
  url?: string;
}

const VideoPlatformsPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'youtube' | 'tiktok' | 'instagram'>('youtube');
  const [trending, setTrending] = useState<VideoContent[]>([]);
  const [influencers, setInfluencers] = useState<Influencer[]>([]);
  const [viral, setViral] = useState<VideoContent[]>([]);
  const [loading, setLoading] = useState(true);
  const [populating, setPopulating] = useState(false);
  const [hasData, setHasData] = useState(false);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [symbolContent, setSymbolContent] = useState<any>(null);

  useEffect(() => {
    checkDataStatus();
  }, []);

  useEffect(() => {
    fetchPlatformData();
  }, [activeTab]);

  const checkDataStatus = async () => {
    try {
      const res = await fetch(apiUrl('/api/video/status'));
      if (res.ok) {
        const data = await res.json();
        setHasData(data.has_data);
      }
    } catch (error) {
      console.error('Error checking video data status:', error);
    }
  };

  const populateSampleData = async () => {
    setPopulating(true);
    try {
      const res = await fetch(apiUrl('/api/video/populate'), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        console.log('Sample data populated:', data);
        setHasData(true);
        await fetchPlatformData();
      } else {
        console.error('Failed to populate sample data');
      }
    } catch (error) {
      console.error('Error populating sample data:', error);
    }
    setPopulating(false);
  };

  const fetchPlatformData = async () => {
    setLoading(true);
    try {
      const [trendingRes, influencersRes, viralRes] = await Promise.all([
        fetch(apiUrl(`/api/video/trending/${activeTab}?limit=10`)),
        fetch(apiUrl(`/api/video/influencers/${activeTab}/top`)),
        fetch(apiUrl('/api/video/viral?min_viral_score=60')),
      ]);

      if (trendingRes.ok) {
        const data = await trendingRes.json();
        setTrending(data.trending || []);
      }
      if (influencersRes.ok) {
        const data = await influencersRes.json();
        setInfluencers(data.influencers || []);
      }
      if (viralRes.ok) {
        const data = await viralRes.json();
        setViral(data.viral_content || []);
      }
    } catch (error) {
      console.error('Error fetching video data:', error);
    }
    setLoading(false);
  };

  const searchSymbolContent = async () => {
    if (!searchSymbol.trim()) return;
    try {
      const res = await fetch(apiUrl(`/api/video/symbol/${searchSymbol.toUpperCase()}`));
      if (res.ok) {
        const data = await res.json();
        setSymbolContent(data);
      }
    } catch (error) {
      console.error('Error searching symbol:', error);
    }
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      youtube: '📺',
      tiktok: '🎵',
      instagram: '📸',
    };
    return icons[platform] || '📱';
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          📹 Video Platforms
        </h2>
        <div className="flex gap-2">
          {!hasData && (
            <button
              onClick={populateSampleData}
              disabled={populating}
              className="px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors text-sm disabled:opacity-50"
            >
              {populating ? 'Loading...' : '📥 Load Sample Data'}
            </button>
          )}
          <button
            onClick={fetchPlatformData}
            className="px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition-colors text-sm"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Platform Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { id: 'youtube', label: '📺 YouTube', color: 'red' },
          { id: 'tiktok', label: '🎵 TikTok', color: 'pink' },
          { id: 'instagram', label: '📸 Instagram', color: 'purple' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? tab.id === 'youtube' ? 'bg-red-600 text-white' :
                  tab.id === 'tiktok' ? 'bg-pink-600 text-white' :
                  'bg-purple-600 text-white'
                : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Search Symbol */}
      <div className="flex gap-2 mb-6">
        <input
          type="text"
          value={searchSymbol}
          onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
          placeholder="Search symbol videos (e.g., NVDA)"
          className="flex-1 px-4 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
          onKeyDown={(e) => e.key === 'Enter' && searchSymbolContent()}
        />
        <button
          onClick={searchSymbolContent}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Search
        </button>
      </div>

      {/* Symbol Content Results */}
      {symbolContent && (
        <div className="mb-6 p-4 bg-slate-900/50 rounded-lg border border-slate-600/50">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-bold text-white">${symbolContent.symbol} Video Content</h3>
            <button onClick={() => setSymbolContent(null)} className="text-slate-400 hover:text-white">✕</button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center p-3 bg-slate-800/50 rounded-lg">
              <div className="text-2xl font-bold text-blue-400">{symbolContent.content_count}</div>
              <div className="text-xs text-slate-400">Videos</div>
            </div>
            <div className="text-center p-3 bg-slate-800/50 rounded-lg">
              <div className="text-2xl font-bold text-green-400">{formatNumber(symbolContent.total_views)}</div>
              <div className="text-xs text-slate-400">Total Views</div>
            </div>
            <div className="text-center p-3 bg-slate-800/50 rounded-lg">
              <div className={`text-2xl font-bold ${symbolContent.avg_sentiment > 0.2 ? 'text-green-400' : symbolContent.avg_sentiment < -0.2 ? 'text-red-400' : 'text-yellow-400'}`}>
                {symbolContent.sentiment_label}
              </div>
              <div className="text-xs text-slate-400">Sentiment</div>
            </div>
            <div className="text-center p-3 bg-slate-800/50 rounded-lg">
              <div className="text-lg font-bold text-white">
                {Object.entries(symbolContent.by_platform || {}).map(([p, c]) => (
                  <span key={p} className="mr-2">{getPlatformIcon(p)}{c as number}</span>
                ))}
              </div>
              <div className="text-xs text-slate-400">By Platform</div>
            </div>
          </div>
        </div>
      )}

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trending Videos */}
        <div>
          <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
            🔥 Trending on {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}
          </h3>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
              </div>
            ) : trending.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-slate-400 text-sm mb-3">No trending content available</p>
                {!hasData && (
                  <button
                    onClick={populateSampleData}
                    disabled={populating}
                    className="px-4 py-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors text-sm disabled:opacity-50"
                  >
                    {populating ? 'Loading...' : '📥 Load Sample Data'}
                  </button>
                )}
              </div>
            ) : (
              trending.map((video) => (
                <a 
                  key={video.id} 
                  href={video.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer group"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-xl">{getPlatformIcon(video.platform)}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white font-medium truncate group-hover:text-blue-400 transition-colors">{video.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-slate-400">{video.creator?.name}</span>
                        {video.creator?.verified && <span className="text-xs text-blue-400">✓</span>}
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                        <span>👁 {formatNumber(video.engagement?.views || 0)}</span>
                        <span>❤️ {formatNumber(video.engagement?.likes || 0)}</span>
                        <span className={`px-1.5 py-0.5 rounded ${video.analysis?.viral_score >= 70 ? 'bg-red-500/20 text-red-400' : 'bg-slate-600/50 text-slate-400'}`}>
                          🔥 {video.analysis?.viral_score?.toFixed(0) || 0}
                        </span>
                      </div>
                      {video.analysis?.symbols?.length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {video.analysis.symbols.map((sym) => (
                            <span key={sym} className="px-1.5 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded">
                              ${sym}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <span className="text-slate-500 group-hover:text-blue-400 transition-colors shrink-0">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </span>
                  </div>
                </a>
              ))
            )}
          </div>
        </div>

        {/* Top Influencers */}
        <div>
          <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
            ⭐ Top Finance Influencers
          </h3>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {influencers.length === 0 ? (
              <p className="text-slate-400 text-center py-4 text-sm">No influencers data</p>
            ) : (
              influencers.map((influencer, i) => (
                <a 
                  key={influencer.handle} 
                  href={influencer.url || `https://www.google.com/search?q=${encodeURIComponent(influencer.name)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400 text-sm w-6">#{i + 1}</span>
                    <div>
                      <p className="text-white font-medium group-hover:text-blue-400 transition-colors">{influencer.name}</p>
                      <p className="text-xs text-slate-400">@{influencer.handle}</p>
                    </div>
                  </div>
                  <div className="text-right flex items-center gap-3">
                    <div>
                      <p className="text-sm font-bold text-blue-400">{formatNumber(influencer.followers)}</p>
                      <div className="flex gap-1 mt-1">
                        {influencer.focus?.slice(0, 2).map((f) => (
                          <span key={f} className="px-1.5 py-0.5 text-xs bg-slate-600/50 text-slate-300 rounded">
                            {f}
                          </span>
                        ))}
                      </div>
                    </div>
                    <span className="text-slate-500 group-hover:text-blue-400 transition-colors">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </span>
                  </div>
                </a>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Viral Alerts */}
      {viral.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
            🚨 Viral Alerts (Score 60+)
          </h3>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {viral.slice(0, 5).map((v) => (
              <a 
                key={v.id} 
                href={v.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-shrink-0 p-3 bg-gradient-to-r from-red-500/20 to-orange-500/20 rounded-lg border border-red-500/30 min-w-[200px] hover:from-red-500/30 hover:to-orange-500/30 transition-colors cursor-pointer group"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{getPlatformIcon(v.platform)}</span>
                    <span className="text-lg font-bold text-white">🔥 {v.analysis?.viral_score?.toFixed(0)}</span>
                  </div>
                  <span className="text-slate-500 group-hover:text-white transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </span>
                </div>
                <p className="text-sm text-white truncate group-hover:text-blue-400 transition-colors">{v.title}</p>
                <p className="text-xs text-slate-400 mt-1">{v.creator?.name}</p>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoPlatformsPanel;

