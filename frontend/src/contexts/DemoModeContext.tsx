import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';

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
  // Easter egg for MIN mode unlock
  easterEggClicks: number;
  incrementEasterEgg: () => boolean; // Returns true if 7 clicks reached
  resetEasterEgg: () => void;
  showUnlockPrompt: boolean;
  setShowUnlockPrompt: (show: boolean) => void;
}

const DemoModeContext = createContext<DemoModeContextType | undefined>(undefined);

// Check if running in demo mode (GitLab/NVIDIA internal build)
const checkDemoMode = (): boolean => {
  // Demo mode is enabled if:
  // 1. VITE_DEMO_MODE env var is set to 'true'
  // 2. Or running from NVIDIA GitLab (gitlab-master.nvidia.com)
  // 3. Or running from any GitLab instance
  // 4. Or running from foresight.nvidia.com (MIN deployment)
  const envDemoMode = (import.meta as any).env?.VITE_DEMO_MODE === 'true';
  
  const hostname = window.location.hostname;
  
  // NVIDIA Foresight - MIN MODE (restricted)
  const isForesight = hostname.includes('foresight.nvidia.com') || 
                      hostname.includes('foresight');
  
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
  
  // Demo/MIN mode on: NVIDIA Foresight, NVIDIA GitLab, public GitLab, or if env var is set
  return envDemoMode || isForesight || isNvidiaGitLab || isPublicGitLab;
};

// Easter egg unlock password for MIN mode
const MIN_UNLOCK_PASSWORD = '106431';
// Legacy password for other deployments
const UNLOCK_PASSWORD = 'xfactor2025';
// Number of clicks required to trigger easter egg
const EASTER_EGG_CLICKS_REQUIRED = 7;

export function DemoModeProvider({ children }: { children: ReactNode }) {
  const [isDemoMode] = useState(checkDemoMode);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [easterEggClicks, setEasterEggClicks] = useState(0);
  const [showUnlockPrompt, setShowUnlockPrompt] = useState(false);
  const [lastClickTime, setLastClickTime] = useState(0);
  
  // Determine edition based on demo mode
  // XFactor-botMax: Full features (GitHub, localhost, desktop app)
  // XFactor-botMin: Restricted features (GitLab/Foresight deployments)
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

  // Easter egg: increment click counter
  const incrementEasterEgg = useCallback((): boolean => {
    const now = Date.now();
    
    // Reset counter if more than 2 seconds between clicks
    if (now - lastClickTime > 2000) {
      setEasterEggClicks(1);
      setLastClickTime(now);
      return false;
    }
    
    setLastClickTime(now);
    const newCount = easterEggClicks + 1;
    setEasterEggClicks(newCount);
    
    // Check if easter egg triggered (7 clicks)
    if (newCount >= EASTER_EGG_CLICKS_REQUIRED) {
      setShowUnlockPrompt(true);
      setEasterEggClicks(0);
      return true;
    }
    
    return false;
  }, [easterEggClicks, lastClickTime]);

  const resetEasterEgg = useCallback(() => {
    setEasterEggClicks(0);
    setLastClickTime(0);
  }, []);

  const unlock = (password: string): boolean => {
    // Accept both MIN unlock password and legacy password
    if (password === MIN_UNLOCK_PASSWORD || password === UNLOCK_PASSWORD) {
      setIsUnlocked(true);
      sessionStorage.setItem('xfactor_unlocked', 'true');
      setShowUnlockPrompt(false);
      return true;
    }
    return false;
  };

  const lock = () => {
    setIsUnlocked(false);
    sessionStorage.removeItem('xfactor_unlocked');
    resetEasterEgg();
  };

  return (
    <DemoModeContext.Provider value={{ 
      isDemoMode, 
      isUnlocked, 
      edition, 
      editionLabel, 
      unlock, 
      lock,
      easterEggClicks,
      incrementEasterEgg,
      resetEasterEgg,
      showUnlockPrompt,
      setShowUnlockPrompt
    }}>
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

