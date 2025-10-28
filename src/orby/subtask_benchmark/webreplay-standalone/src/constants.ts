import path from 'path';

// Get the directory where the executable is located
export const executableDir = path.dirname(process.argv[1]);
export const rootPath = process.cwd();

// Base directory where replay files are located
export const replaysPath = process.cwd();

// Used for extension related functionality
export const extensionId = 'hijnmoemdldebjokiebfcalfjkkdnejb';

// Path to the Orby extension, customize this to point to your extension
export const orbotExtensionDist = process.env.ORBY_EXTENSION_PATH || 
  path.join(rootPath, 'extension/dist'); 