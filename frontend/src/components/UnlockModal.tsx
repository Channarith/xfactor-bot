import { useState } from 'react';
import { X, Lock, Unlock, Shield } from 'lucide-react';
import { useDemoMode } from '../contexts/DemoModeContext';

interface UnlockModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function UnlockModal({ isOpen, onClose }: UnlockModalProps) {
  const { unlock, isUnlocked, lock } = useDemoMode();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleUnlock = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (unlock(password)) {
      setSuccess(true);
      setTimeout(() => {
        onClose();
        setPassword('');
        setSuccess(false);
      }, 1500);
    } else {
      setError('Invalid password. Please try again.');
      setPassword('');
    }
  };

  const handleLock = () => {
    lock();
    onClose();
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div 
        className="bg-slate-900 rounded-xl shadow-2xl w-full max-w-md overflow-hidden border border-slate-700"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700 bg-gradient-to-r from-amber-600/20 to-orange-600/20">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/20 rounded-lg">
              <Shield className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">
                {isUnlocked ? 'Full Access Enabled' : 'Demo Mode Active'}
              </h2>
              <p className="text-sm text-slate-400">
                {isUnlocked ? 'All features are unlocked' : 'Enter password to unlock all features'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {success ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Unlock className="w-8 h-8 text-green-400" />
              </div>
              <h3 className="text-xl font-semibold text-green-400 mb-2">Access Granted!</h3>
              <p className="text-slate-400">All features are now unlocked.</p>
            </div>
          ) : isUnlocked ? (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Unlock className="w-8 h-8 text-green-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Full Access Active</h3>
              <p className="text-slate-400 mb-6">
                You have access to all features including broker connections and live trading.
              </p>
              <button
                onClick={handleLock}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors flex items-center gap-2 mx-auto"
              >
                <Lock className="w-4 h-4" />
                Lock Features
              </button>
            </div>
          ) : (
            <>
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 mb-6">
                <h4 className="text-amber-400 font-medium mb-2">Demo Mode Restrictions</h4>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Broker connections disabled</li>
                  <li>• Live market data unavailable</li>
                  <li>• Real trading disabled</li>
                  <li>• Paper trading only</li>
                </ul>
              </div>

              <form onSubmit={handleUnlock}>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Enter Unlock Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password..."
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                  autoFocus
                />
                
                {error && (
                  <p className="mt-2 text-sm text-red-400">{error}</p>
                )}

                <button
                  type="submit"
                  className="w-full mt-4 px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-semibold rounded-lg transition-all flex items-center justify-center gap-2"
                >
                  <Unlock className="w-5 h-5" />
                  Unlock Full Features
                </button>
              </form>

              <p className="mt-4 text-xs text-slate-500 text-center">
                Contact administrator for access credentials
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

