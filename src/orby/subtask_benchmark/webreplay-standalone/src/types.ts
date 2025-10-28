export interface ReplayEnvStaticPage {
  html?: string;
  filePath?: string;
  serveAtUrl?: string;
  resources?: ReplayEnvResource[];
}

export interface ReplayEnvResource {
  filePath?: string;
  serveAtPath?: string;
  requireBuild?: boolean;
}

export interface ReplayEnv {
  warcFilePath?: string;
  startUrl?: string;
  staticPages?: ReplayEnvStaticPage[];
}

export interface ReplayAction {
  setValue?: {
    fieldLocator: {
      jsonValue: string;
    };
    fieldValue: {
      jsonValue: string;
    };
  };
  click?: {
    elementLocator: {
      jsonValue: string;
    };
  };
}

export interface Replay {
  description?: string;
  env?: ReplayEnv;
  actions?: ReplayAction[];
} 