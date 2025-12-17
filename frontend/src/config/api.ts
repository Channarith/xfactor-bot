/**
 * API Configuration for XFactor Bot
 * 
 * Automatically patches fetch for Tauri desktop environment.
 */

// Check if we're running in Tauri (desktop)
// More robust check for different Tauri versions and environments
const isTauri = typeof window !== 'undefined' && (
  '__TAURI__' in window || 
  '__TAURI_INTERNALS__' in window ||
  // Check for Tauri-specific protocols
  window.location.protocol === 'tauri:' ||
  window.location.protocol === 'https:' && window.location.hostname === 'tauri.localhost' ||
  // Fallback: Check if we're NOT in a normal browser context
  (window.location.protocol !== 'http:' && window.location.protocol !== 'https:' && window.location.protocol !== 'file:')
);

// Backend URL for desktop app - use 127.0.0.1 instead of localhost for better compatibility
const DESKTOP_API_URL = 'http://127.0.0.1:9876';

// Store original fetch
const originalFetch = window.fetch.bind(window);

// Patched fetch that rewrites relative URLs for Tauri
const patchedFetch: typeof fetch = async (input, init?) => {
  let url: string;
  let requestInit = init;
  
  // Handle Request objects
  if (input instanceof Request) {
    url = input.url;
    // Clone init from Request if not provided
    if (!requestInit) {
      requestInit = {
        method: input.method,
        headers: input.headers,
        body: input.body,
        mode: input.mode,
        credentials: input.credentials,
        cache: input.cache,
        redirect: input.redirect,
        referrer: input.referrer,
        integrity: input.integrity,
      };
    }
  } else if (typeof input === 'string') {
    url = input;
  } else {
    url = String(input);
  }
  
  // Check if this is a relative API URL that needs rewriting
  const needsRewrite = url.startsWith('/api') || 
                       url.startsWith('/health') || 
                       url.startsWith('/metrics');
  
  if (needsRewrite) {
    const newUrl = `${DESKTOP_API_URL}${url}`;
    console.log(`[API] Rewriting ${url} -> ${newUrl}`);
    
    try {
      return await originalFetch(newUrl, requestInit);
    } catch (error) {
      console.error(`[API] Fetch failed for ${newUrl}:`, error);
      throw error;
    }
  }
  
  // Handle WebSocket URLs (though fetch doesn't work for WebSocket)
  if (url.startsWith('/ws')) {
    const newUrl = `ws://127.0.0.1:9876${url}`;
    console.log(`[API] WebSocket URL: ${newUrl}`);
    return originalFetch(newUrl, requestInit);
  }
  
  return originalFetch(input, init);
};

// Apply patch if running in Tauri
if (isTauri) {
  console.log('[API] Running in Tauri desktop mode - patching fetch for 127.0.0.1:9876');
  window.fetch = patchedFetch;
} else {
  console.log('[API] Running in browser mode - using relative URLs');
}

// Export utilities
export const getApiBaseUrl = (): string => {
  return isTauri ? DESKTOP_API_URL : '';
};

export const getWsBaseUrl = (): string => {
  if (isTauri) {
    return 'ws://127.0.0.1:9876';
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}`;
};

export const isDesktopApp = isTauri;

/**
 * Helper function to construct API URLs.
 * In Tauri, prepends 127.0.0.1:9876 to relative paths.
 * In browser, returns path as-is (handled by patched fetch).
 */
export const apiUrl = (path: string): string => {
  if (isTauri && path.startsWith('/')) {
    return `${DESKTOP_API_URL}${path}`;
  }
  return path;
};

/**
 * Debug function to check API configuration
 */
export const debugApiConfig = () => {
  console.log('[API Debug]', {
    isTauri,
    protocol: window.location.protocol,
    hostname: window.location.hostname,
    apiBaseUrl: getApiBaseUrl(),
    wsBaseUrl: getWsBaseUrl(),
    hasTauriGlobal: '__TAURI__' in window,
    hasTauriInternals: '__TAURI_INTERNALS__' in window,
  });
};

// Auto-run debug on load
if (typeof window !== 'undefined') {
  debugApiConfig();
}
