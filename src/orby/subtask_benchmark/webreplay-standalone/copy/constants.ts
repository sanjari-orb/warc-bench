import path from 'path';

export const rootPath = path.resolve('.', '../..');

export const replaysPath = path.join(rootPath, 'packages/webreplay/replays/');

export const applicationsPath = path.join(
  rootPath,
  'packages/webreplay/replays/applications',
);

export const componentsPath = path.join(
  rootPath,
  'packages/webreplay/replays/components',
);

export const modulesPath = path.join(
  rootPath,
  'packages/webreplay/src/env/modules',
);
export const archivesFolderPath = path.join(replaysPath, 'applications');

export const orbotExtensionDist = path.join(
  rootPath,
  'packages/extension/dist',
);
export const recordingOverrideMainPath = path.join(
  orbotExtensionDist,
  'recording-override-main.js',
);
export const overrideMainPath = path.join(
  orbotExtensionDist,
  'override-main.js',
);
export const archiveWebExtensionDist = path.join(
  rootPath,
  'packages/webrecorder/dist',
);
export const protoRootPath = path.join(rootPath, 'protos');
export const protocPath = path.join(rootPath, 'node_modules/.bin/protoc');

export const extensionId = 'hijnmoemdldebjokiebfcalfjkkdnejb';

export const notMatchMsg = 'Generated actions does not match expected';
