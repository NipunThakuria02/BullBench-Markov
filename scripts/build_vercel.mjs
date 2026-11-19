/** Build a public frontend without mutating or publishing local private assets. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
process.chdir(root);
let temp;
try {
 const supplied=process.env.VITE_API_BASE_URL;
 if(!supplied)throw Error('Set VITE_API_BASE_URL to your actual HTTPS backend origin in Vercel. Deploy the Python backend first.');
 const url=new URL(supplied);
 if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||url.pathname!=='/')throw Error('VITE_API_BASE_URL must be a bare HTTPS backend origin.');
 const config=JSON.parse(fs.readFileSync('vercel.json','utf8'));
 const csp=config.headers.flatMap(r=>r.headers).find(h=>h.key.toLowerCase()==='content-security-policy')?.value||'';
 const connect=csp.split(';').find(item=>item.trim().startsWith('connect-src '))?.trim().split(/\s+/)||[];
 if(!connect.includes(url.origin))throw Error(`Backend origin is absent from CSP. Run: python scripts/configure_api_host.py ${url.origin}, commit vercel.json, then redeploy.`);
 temp=fs.mkdtempSync(path.join(os.tmpdir(),'bullbench-public-'));
 // Only reviewed branding assets enter the public build, even when called from a private local ZIP.
 for(const name of ['favicon.svg','fonts','logos']){
  const source=path.join(root,'web/public',name);
  if(fs.existsSync(source))fs.cpSync(source,path.join(temp,name),{recursive:true});
 }
 const run=spawnSync(process.platform==='win32'?'npm.cmd':'npm',['--prefix','web','run','build','--','--outDir','dist-vercel'],{stdio:'inherit',env:{...process.env,VITE_API_BASE_URL:url.origin,BULLBENCH_PUBLIC_DIR:temp}});
 if(run.error)throw run.error;
 if(run.status!==0)throw Error(`Frontend build failed (${run.status}).`);
 const forbidden=['results.json','history'];
 for(const name of forbidden)if(fs.existsSync(path.join('web/dist-vercel',name)))throw Error(`Private static asset leaked: ${name}`);
 console.log('Vercel frontend ready in web/dist-vercel; private datasets, models and legacy snapshots excluded.');
} catch(error){console.error(error.message);process.exitCode=1;} finally {if(temp)fs.rmSync(temp,{recursive:true,force:true});}
