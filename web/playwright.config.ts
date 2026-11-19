import { defineConfig } from '@playwright/test';
export default defineConfig({
 testDir:'./tests',fullyParallel:true,workers:2,
 use:{headless:true,launchOptions:process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}},
 reporter:'list',
 projects:[
  {name:'markovlab',testMatch:'markov.spec.ts',use:{baseURL:'http://127.0.0.1:8100'}},
  {name:'legacy',testMatch:'dashboard.spec.ts',use:{baseURL:'http://127.0.0.1:8101'}}
 ],
 webServer:[
  {command:'npm run preview -- --port 8100',port:8100,reuseExistingServer:false},
  {command:'VITE_LEGACY_DASHBOARD=1 npx vite build --outDir dist-legacy && npx vite preview --outDir dist-legacy --host 127.0.0.1 --port 8101 --strictPort',port:8101,reuseExistingServer:false}
 ]
});
