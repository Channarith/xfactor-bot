import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// Declare Tauri global for TypeScript
declare global {
  interface Window {
    __TAURI__?: unknown;
  }
}

// Version branding
export type ProductEdition = 'XFactor-botMax' | 'XFactor-botMin';

interface DemoModeContextType {
  isDemoMode: boolean;
  isUnlocked: boolean;
  edition: ProductEdition;
  editionLabel: string;
  unlock: (password: string) => boolean;
  lock: () => void;
}

const DemoModeContext = createContext<DemoModeContextType | undefined>(undefined);

// Check if running in demo mode (GitLab/NVIDIA internal build)
const checkDemoMode = (): boolean => {
  // Demo mode is enabled if:
  // 1. VITE_DEMO_MODE env var is set to 'true'
  // 2. Or running from NVIDIA GitLab (gitlab-master.nvidia.com)
  // 3. Or running from any GitLab instance
  const envDemoMode = (import.meta as any).env?.VITE_DEMO_MODE === 'true';
  
  const hostname = window.location.hostname;
  
  // NVIDIA GitLab - DEMO MODE (restricted)
  const isNvidiaGitLab = hostname.includes('nvidia.com') || 
                         hostname.includes('gitlab-master');
  
  // Public GitLab - DEMO MODE (restricted)
  const isPublicGitLab = hostname.includes('gitlab.io') || 
                         hostname.includes('gitlab.com');
  
  // Full features environments (NO restrictions)
  const isLocalhost = hostname === 'localhost' || 
                      hostname === '127.0.0.1';
  const isGitHub = hostname.includes('github.io') || 
                   hostname.includes('github.com');
  const isTauriDesktop = window.__TAURI__ !== undefined;
  
  // Full features on: localhost, GitHub, and Tauri desktop app
  if (isLocalhost || isGitHub || isTauriDesktop) {
    return false; // Full features - NO demo mode
  }
  
  // Demo mode on: NVIDIA GitLab, public GitLab, or if env var is set
  return envDemoMode || isNvidiaGitLab || isPublicGitLab;
};

// The unlock password - in production, this should be more secure
const UNLOCK_PASSWORD = 'xfactor2025';

export function DemoModeProvider({ children }: { children: ReactNode }) {
  const [isDemoMode] = useState(checkDemoMode);
  const [isUnlocked, setIsUnlocked] = useState(false);
  
  // Determine edition based on demo mode
  // XFactor-botMax: Full features (GitHub, localhost, desktop app)
  // XFactor-botMin: Restricted features (GitLab deployments)
  const edition: ProductEdition = isDemoMode ? 'XFactor-botMin' : 'XFactor-botMax';
  const editionLabel = isDemoMode 
    ? 'XFactor-botMin (Restricted)' 
    : 'XFactor-botMax (Full Features)';

  // Check for stored unlock state
  useEffect(() => {
    const stored = sessionStorage.getItem('xfactor_unlocked');
    if (stored === 'true' && isDemoMode) {
      setIsUnlocked(true);
    }
  }, [isDemoMode]);

  const unlock = (password: string): boolean => {
    if (password === UNLOCK_PASSWORD) {
      setIsUnlocked(true);
      sessionStorage.setItem('xfactor_unlocked', 'true');
      return true;
    }
    return false;
  };

  const lock = () => {
    setIsUnlocked(false);
    sessionStorage.removeItem('xfactor_unlocked');
  };

  return (
    <DemoModeContext.Provider value={{ isDemoMode, isUnlocked, edition, editionLabel, unlock, lock }}>
      {children}
    </DemoModeContext.Provider>
  );
}

export function useDemoMode() {
  const context = useContext(DemoModeContext);
  if (context === undefined) {
    throw new Error('useDemoMode must be used within a DemoModeProvider');
  }
  return context;
}

// Helper hook to check if a feature is available
export function useFeatureAvailable() {
  const { isDemoMode, isUnlocked } = useDemoMode();
  
  return {
    // Full features available if not in demo mode, or if unlocked
    isFullFeaturesAvailable: !isDemoMode || isUnlocked,
    // Broker connections require unlock in demo mode
    canConnectBroker: !isDemoMode || isUnlocked,
    // Live data requires unlock in demo mode
    canUseLiveData: !isDemoMode || isUnlocked,
    // Trading requires unlock in demo mode
    canTrade: !isDemoMode || isUnlocked,
  };
}

