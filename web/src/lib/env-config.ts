// Environment variables utility
// This utility helps access environment variables both at build time and runtime

declare global {
  interface Window {
    __ENV__?: {
      NEXT_PUBLIC_SERVER_URL: string;
      NEXT_PUBLIC_API_PORT: string;
      NEXT_PUBLIC_UI_PORT: string;
    };
  }
}

class EnvironmentConfig {
  private static instance: EnvironmentConfig;
  
  private constructor() {}
  
  public static getInstance(): EnvironmentConfig {
    if (!EnvironmentConfig.instance) {
      EnvironmentConfig.instance = new EnvironmentConfig();
    }
    return EnvironmentConfig.instance;
  }
  
  public getServerUrl(): string {
    // Try runtime config first, then build-time config
    if (typeof window !== 'undefined' && window.__ENV__) {
      return window.__ENV__.NEXT_PUBLIC_SERVER_URL || '';
    }
    return process.env.NEXT_PUBLIC_SERVER_URL || '';
  }
  
  public getApiPort(): string {
    if (typeof window !== 'undefined' && window.__ENV__) {
      return window.__ENV__.NEXT_PUBLIC_API_PORT || '';
    }
    return process.env.NEXT_PUBLIC_API_PORT || '';
  }
  
  public getUiPort(): string {
    if (typeof window !== 'undefined' && window.__ENV__) {
      return window.__ENV__.NEXT_PUBLIC_UI_PORT || '';
    }
    return process.env.NEXT_PUBLIC_UI_PORT || '';
  }
  
  public getApiUrl(): string {
    const serverUrl = this.getServerUrl();
    const apiPort = this.getApiPort();
    
    if (serverUrl && apiPort) {
      return `${serverUrl}:${apiPort}`;
    }
    
    // Fallback to build-time configuration
    return process.env.NEXT_PUBLIC_SERVER_URL + ':' + process.env.NEXT_PUBLIC_API_PORT || '';
  }
}

export const envConfig = EnvironmentConfig.getInstance();