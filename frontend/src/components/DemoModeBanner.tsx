import { useDemoMode } from '../contexts/DemoModeContext';

export default function DemoModeBanner() {
  const { isDemoMode, isUnlocked } = useDemoMode();

  // MIN mode: Don't show any banner - the UI already indicates MIN mode
  // The locked features panel in Dashboard provides clear guidance
  if (!isDemoMode || isUnlocked) return null;

  // Return nothing - no banner for MIN mode
  // Easter egg hint is in the Dashboard's locked panel
  return null;
}

