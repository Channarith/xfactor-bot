/**
 * Audio utilities for text-to-speech and speech recognition
 * Uses Web Speech API for browser-native functionality
 */

// Check if speech synthesis is supported
export const isSpeechSynthesisSupported = () => {
  return 'speechSynthesis' in window;
};

// Check if speech recognition is supported
export const isSpeechRecognitionSupported = () => {
  return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
};

// Text-to-speech function
export const speak = (text: string, options?: {
  rate?: number;
  pitch?: number;
  volume?: number;
  voice?: string;
  onEnd?: () => void;
  onError?: (error: string) => void;
}): SpeechSynthesisUtterance | null => {
  if (!isSpeechSynthesisSupported()) {
    options?.onError?.('Speech synthesis not supported in this browser');
    return null;
  }

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = options?.rate ?? 1.0;
  utterance.pitch = options?.pitch ?? 1.0;
  utterance.volume = options?.volume ?? 1.0;

  // Try to get a good voice
  const voices = window.speechSynthesis.getVoices();
  if (options?.voice) {
    const selectedVoice = voices.find(v => v.name.includes(options.voice!));
    if (selectedVoice) utterance.voice = selectedVoice;
  } else {
    // Prefer English voices
    const englishVoice = voices.find(v => v.lang.startsWith('en-') && v.localService);
    if (englishVoice) utterance.voice = englishVoice;
  }

  if (options?.onEnd) {
    utterance.onend = options.onEnd;
  }
  
  if (options?.onError) {
    utterance.onerror = (e) => options.onError?.(e.error);
  }

  window.speechSynthesis.speak(utterance);
  return utterance;
};

// Stop speaking
export const stopSpeaking = () => {
  if (isSpeechSynthesisSupported()) {
    window.speechSynthesis.cancel();
  }
};

// Check if currently speaking
export const isSpeaking = (): boolean => {
  return isSpeechSynthesisSupported() && window.speechSynthesis.speaking;
};

// Get available voices
export const getVoices = (): SpeechSynthesisVoice[] => {
  if (!isSpeechSynthesisSupported()) return [];
  return window.speechSynthesis.getVoices();
};

// Speech recognition type
interface SpeechRecognitionEvent {
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string;
        confidence: number;
      };
      isFinal: boolean;
    };
    length: number;
  };
}

// Create speech recognition instance
export const createSpeechRecognition = (options?: {
  continuous?: boolean;
  interimResults?: boolean;
  language?: string;
  onResult?: (transcript: string, isFinal: boolean) => void;
  onEnd?: () => void;
  onError?: (error: string) => void;
}): any => {
  if (!isSpeechRecognitionSupported()) {
    options?.onError?.('Speech recognition not supported in this browser');
    return null;
  }

  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  const recognition = new SpeechRecognition();

  recognition.continuous = options?.continuous ?? false;
  recognition.interimResults = options?.interimResults ?? true;
  recognition.lang = options?.language ?? 'en-US';

  recognition.onresult = (event: SpeechRecognitionEvent) => {
    const lastResult = event.results[event.results.length - 1];
    const transcript = lastResult[0].transcript;
    const isFinal = lastResult.isFinal;
    options?.onResult?.(transcript, isFinal);
  };

  recognition.onend = () => {
    options?.onEnd?.();
  };

  recognition.onerror = (event: any) => {
    options?.onError?.(event.error);
  };

  return recognition;
};

// Format data for speaking (make it more natural)
export const formatForSpeech = (data: {
  totalValue?: number;
  dailyPnL?: number;
  dailyPnLPct?: number;
  openPositions?: number;
  newsSummary?: string;
}): string => {
  const parts: string[] = [];

  if (data.totalValue !== undefined) {
    parts.push(`Your portfolio value is ${formatCurrency(data.totalValue)}.`);
  }

  if (data.dailyPnL !== undefined && data.dailyPnLPct !== undefined) {
    const direction = data.dailyPnL >= 0 ? 'up' : 'down';
    parts.push(`Today's performance is ${direction} ${formatCurrency(Math.abs(data.dailyPnL))}, or ${Math.abs(data.dailyPnLPct).toFixed(2)} percent.`);
  }

  if (data.openPositions !== undefined) {
    parts.push(`You have ${data.openPositions} open positions.`);
  }

  if (data.newsSummary) {
    parts.push(`News summary: ${data.newsSummary}`);
  }

  return parts.join(' ');
};

// Helper to format currency for speech
const formatCurrency = (value: number): string => {
  if (Math.abs(value) >= 1000000) {
    return `${(value / 1000000).toFixed(2)} million dollars`;
  } else if (Math.abs(value) >= 1000) {
    return `${(value / 1000).toFixed(2)} thousand dollars`;
  }
  return `${value.toFixed(2)} dollars`;
};

// Speak news headlines
export const speakNewsHeadlines = (headlines: { ticker: string; headline: string; sentiment: number }[]): void => {
  const text = headlines.map((h, i) => {
    const sentiment = h.sentiment > 0.2 ? 'bullish' : h.sentiment < -0.2 ? 'bearish' : 'neutral';
    return `${i + 1}. ${h.ticker}: ${h.headline}. Sentiment is ${sentiment}.`;
  }).join(' ');

  speak(`Here are the latest headlines. ${text}`, {
    rate: 0.95,
  });
};

// Speak portfolio summary
export const speakPortfolioSummary = (summary: {
  totalValue: number;
  dailyPnL: number;
  dailyPnLPct: number;
  openPositions: number;
  topGainer?: { symbol: string; change: number };
  topLoser?: { symbol: string; change: number };
}): void => {
  let text = formatForSpeech(summary);
  
  if (summary.topGainer) {
    text += ` Your top gainer is ${summary.topGainer.symbol}, up ${summary.topGainer.change.toFixed(1)} percent.`;
  }
  
  if (summary.topLoser) {
    text += ` Your top loser is ${summary.topLoser.symbol}, down ${Math.abs(summary.topLoser.change).toFixed(1)} percent.`;
  }

  speak(text, {
    rate: 0.95,
  });
};

