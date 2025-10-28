## injected-agent.js

To build a new binary of Chrome extension content script,

```
git clone --recursive git@github.com:orby-ai-engineering/orby-web-app.git
git checkout webpack-agent
cd packages/extension
yarn install
npm run build:agent-prod
```

Then you will find this file under the `dist` folder.