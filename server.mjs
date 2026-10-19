import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {initialState,validateState} from './dist/engine.mjs';
import {galaxies,validateGalaxyState} from './dist/galaxies.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
const port=Number(process.env.FLEET_PORT||4173);
const storage=process.env.FLEET_DATA_DIR ? path.resolve(process.env.FLEET_DATA_DIR) : path.join(root,'local-data');
fs.mkdirSync(storage,{recursive:true});
const stateFile=galaxy=>path.join(storage,galaxy==='g6'?'state.json':`state-${galaxy}.json`);
const json=(res,status,data)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(data));};
function readState(galaxy){const file=stateFile(galaxy);return fs.existsSync(file)?validateGalaxyState(validateState(JSON.parse(fs.readFileSync(file,'utf8'))),galaxy):initialState(galaxy);}
const server=http.createServer(async(req,res)=>{
  try {
    const host=req.headers.host;
    if(![`127.0.0.1:${port}`,`localhost:${port}`].includes(host)) return json(res,403,{error:'Loopback host required.'});
    if(req.headers.origin && req.headers.origin!==`http://${host}`) return json(res,403,{error:'Cross-origin requests are not allowed.'});
    const url=new URL(req.url,`http://${host}`);
    if(url.pathname==='/api/health') return json(res,200,{app:'galaxies-fleet-planner',root});
    if(url.pathname==='/api/state') {
      const galaxy=url.searchParams.get('galaxy')||'g6';
      if(!galaxies.some(g=>g.id===galaxy))return json(res,400,{error:'Unknown galaxy.'});
      const statePath=stateFile(galaxy);
      if(req.method==='GET') return json(res,200,readState(galaxy));
      if(req.method!=='PUT' || req.headers['content-type']!=='application/json') return json(res,405,{error:'Use JSON PUT.'});
      let body='';for await(const chunk of req){body+=chunk;if(body.length>2e6)return json(res,413,{error:'Backup is too large.'});}
      let state;try{state=validateGalaxyState(validateState(JSON.parse(body)),galaxy);}catch(e){return json(res,400,{error:e.message});}
      // Refuse to silently replace a corrupt existing file. Preserve it for recovery.
      readState(galaxy);
      fs.writeFileSync(statePath+'.tmp',JSON.stringify(state,null,2));
      if(fs.existsSync(statePath))fs.copyFileSync(statePath,statePath+'.previous');
      fs.renameSync(statePath+'.tmp',statePath);
      return json(res,200,{saved:true});
    }
    if(req.method!=='GET' && req.method!=='HEAD')return json(res,405,{error:'Read only.'});
    const requested=decodeURIComponent(url.pathname);
    const isImage=requested.startsWith('/source/images/');
    const base=isImage?path.join(root,'source','images'):path.join(root,'dist');
    const relative=isImage?requested.slice('/source/images'.length):requested==='/'?'/index.html':requested;
    const file=path.resolve(base,'.'+relative);
    if(!file.startsWith(base+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return json(res,404,{error:'Not found.'});
    const ext=path.extname(file);
    let type={'.html':'text/html; charset=utf-8','.css':'text/css','.mjs':'text/javascript','.json':'application/json','.jpg':'image/jpeg','.png':'image/png','.webp':'image/webp'}[ext] || 'application/octet-stream';
    if(isImage&&!ext){const fd=fs.openSync(file,'r'),signature=Buffer.alloc(12);try{fs.readSync(fd,signature,0,12,0);}finally{fs.closeSync(fd);}type=signature[0]===137?'image/png':signature[0]===255?'image/jpeg':signature.toString('ascii',0,3)==='GIF'?'image/gif':'image/webp';}
    res.writeHead(200,{'Content-Type':type,'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"});
    if(req.method==='HEAD')res.end();else fs.createReadStream(file).pipe(res);
  }catch(e){json(res,500,{error:e.message});}
});
server.on('error',e=>{console.error(e.code==='EADDRINUSE'?`Port ${port} is already in use. Open the existing planner or set FLEET_PORT.`:e);process.exit(1);});
server.listen(port,'127.0.0.1',()=>console.log(`Fleet planner: http://127.0.0.1:${port}`));
