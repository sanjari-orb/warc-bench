import webpack, { Configuration } from 'webpack';
import { v4 } from 'uuid';
import path from 'path';
import { replaysPath } from '../../constants';
import { logger } from '../logger';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';

const execPromise = promisify(exec);

const buildFolder = path.join(replaysPath, '.build_cache');

/**
 * Basic Webpack configuration that handles TypeScript/JSX and CSS loading.
 */
const baseWebpackConfig: Configuration = {
  mode: 'development',
  module: {
    rules: [
      {
        test: /\.(ts|tsx)$/,
        exclude: /node_modules/,
        use: [
          {
            loader: 'ts-loader',
          },
        ],
      },
      {
        test: /\.css$/i,
        use: [
          {
            loader: 'style-loader',
          },
          {
            loader: 'css-loader',
          },
        ],
      },
    ],
  },
};

export async function buildResource(inputFile: string): Promise<string> {
  // Make sure the dependencies are installed
  logger.info(`Building ${path.resolve(inputFile)}`);
  const workingFolder = path.resolve(path.dirname(inputFile));

  logger.info(`Installing dependency in ${workingFolder}`);
  await execPromise('yarn install', {
    cwd: workingFolder,
  });

  const outputFileName = v4() + '.js';

  const webpackConfig: Configuration = {
    ...baseWebpackConfig,
    context: path.dirname(inputFile),
    entry: inputFile,
    output: {
      filename: outputFileName,
      path: buildFolder,
    },
  };

  const compiler = webpack(webpackConfig);
  return new Promise<string>((resolve, reject) => {
    compiler.run((err, stats) => {
      if (err || stats?.hasErrors()) {
        if (err) {
          logger.error('Compile error: ', err);
        } else if (stats?.hasErrors()) {
          logger.error(
            `stats has error: ${JSON.stringify(stats.toJson(), null, 2)}`,
          );
        }
        reject(err);
        return;
      }

      const outputFile = path.join(buildFolder, outputFileName);
      fs.readFile(outputFile, 'utf-8', (readErr, data) => {
        if (readErr) {
          reject(readErr);
        } else {
          resolve(data);
        }
        fs.rmSync(outputFile);
      });
    });
  });
}
