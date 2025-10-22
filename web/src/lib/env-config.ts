// Environment variables utility
// This utility helps access environment variables both at build time and runtime

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
    return process.env.NEXT_PUBLIC_SERVER_URL || '';
  }
  
  public getApiPort(): string {
    return process.env.NEXT_PUBLIC_API_PORT || '';
  }
  
  public getUiPort(): string {
    return process.env.NEXT_PUBLIC_UI_PORT || '';
  }
  
  public getApiUrl(): string {
    const serverUrl = this.getServerUrl();
    const apiPort = this.getApiPort();
    
    if (serverUrl && apiPort) {
      return `${serverUrl}:${apiPort}`;
    }
    
    // Fallback to default
    return 'http://localhost:8000';
  }
}

export const envConfig = EnvironmentConfig.getInstance();