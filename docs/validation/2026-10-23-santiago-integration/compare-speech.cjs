// Run from agent-starter-react. Deterministic tone; no audio recording.
const fs = require('node:fs'), vm = require('node:vm'), cp = require('node:child_process');
const ts = require(process.cwd() + '/node_modules/typescript');
const path = 'components/avatar/speech-motion.ts';
const results=[];
for(const version of ['before','after']) {
  const source=version==='before' ? cp.execFileSync('git',['show','7a97679:agent-starter-react/'+path],{encoding:'utf8'}) : fs.readFileSync(path,'utf8');
  const scope={exports:{}};
  vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,scope);
  for(const fps of [15,30,60]) {
    const motion=scope.exports.createSpeechMotion();
    const size=version==='before'?2048:1024;
    let onset=null,close=null;
    for(let frame=0;frame<fps*2;frame++) {
      const now=frame/fps;
      const pcm=Float32Array.from({length:size},(_,i)=>{
        const t=now-(size-1-i)/48000;
        return t>=.25&&t<.75? .1*Math.sin(2*Math.PI*900*t):0;
      });
      const spectrum=new Float32Array(size/2).fill(-120);
      if(pcm.some(v=>v!==0)) spectrum[Math.round(900/(48000/size))]=-25;
      const pose=motion.read(pcm,spectrum,48000,1/fps);
      const moving=Math.max(pose.open,pose.round,pose.wide)>=.01;
      if(moving&&onset===null) onset=(now-.25)*1000;
      if(now>=.75&&!moving&&onset!==null&&close===null) close=(now-.75)*1000;
    }
    results.push({version,fps,onset_ms:onset,closure_ms:close});
  }
}
console.log(JSON.stringify({scope:'synthetic-tone-not-live-call',baseline:'7a97679',note:'900 Hz PCM burst .25–.75 s; rolling FFT window and render cadence. No phoneme or speaker alignment.',results},null,2));
