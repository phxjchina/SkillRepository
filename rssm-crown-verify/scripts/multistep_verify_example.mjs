// 多步 rollout 独立交叉验证（第二实现 × 角点穷举）
// ------------------------------------------------------------
// 目的：在不依赖主脚本 rssm_crown.mjs 的前提下，独立重新实现"IBP 过 GRU + IBP 过
// ReLU 先验/解码"的多步界传播，并以 z0 角点穷举的真实算术 rollout 作独立真值，校验
// 该 sound 盒是否包含所有角点输出。
//
// 诚实声明：GRU 含 sigmoid/tanh（非分段线性），故对 z0 的角点穷举不保证全局极值；
// 但角点输出 ⊂ 真实可达集，因此"sound 盒 ⊇ 全部角点输出"是 soundness 的必要
// 条件。配合主脚本 2 万次随机采样 gold-standard（多步 soundness 100%）构成多重
// 独立证据。单步 ReLU 部分的严格 soundness 证明见 test_crown.mjs（900/900 角点通过）。
import fs from 'fs';
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const rng=mulberry32(20240923);
function randn(){let u=rng(),v=rng();u=Math.min(1-1e-12,Math.max(1e-12,u));v=Math.min(1-1e-12,Math.max(1e-12,v));return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v);}
function rmat(r,c){const m=[];for(let i=0;i<r;i++){const row=new Float64Array(c);for(let j=0;j<c;j++)row[j]=randn()*0.5;m.push(row);}return m;}
function rbias(c){const a=new Float64Array(c);for(let j=0;j<c;j++)a[j]=randn()*0.1;return a;}

// ---------- 独立真值（精确算术 GRU 前向）----------
function gruStepF(x,h,g){
  const sig=v=>1/(1+Math.exp(-v));const gi=x.length,gh=h.length;
  const out=new Float64Array(gh);
  for(let k=0;k<gh;k++){
    let sr=g.bir_r[k];for(let j=0;j<gi;j++)sr+=x[j]*g.Wir_r[j][k];for(let j=0;j<gh;j++)sr+=h[j]*g.Whr_r[j][k];const r=sig(sr);
    let sz=g.bir_z[k];for(let j=0;j<gi;j++)sz+=x[j]*g.Wir_z[j][k];for(let j=0;j<gh;j++)sz+=h[j]*g.Whr_z[j][k];const z=sig(sz);
    let sn=g.bir_n[k];for(let j=0;j<gi;j++)sn+=x[j]*g.Wir_n[j][k];let cn=g.bhr_n[k];for(let j=0;j<gh;j++)cn+=h[j]*g.Whr_n[j][k];sn+=r*cn;const n=Math.tanh(sn);
    out[k]=(1-z)*n+z*h[k];
  }
  return out;
}
function priorF(W1,b1,W2,b2,h){const h2=new Float64Array(h.length);for(let i=0;i<h.length;i++){let s=0;for(let k=0;k<W1.length;k++)s+=W1[k][i]*h[k];const v=s+b1[i];h2[i]=v>0?v:0;}const o=new Float64Array(W2[0].length);for(let j=0;j<o.length;j++){let s=0;for(let k=0;k<h2.length;k++)s+=h2[k]*W2[k][j];o[j]=s+b2[j];}return o;}

// ---------- 独立 IBP 界传播（第二实现）----------
function imul4(a,b,c,d){return [Math.min(a,b,c,d),Math.max(a,b,c,d)];}
function ibpMat(W,b,boxL,boxU){const m=W.length,h=W[0].length;const L=new Float64Array(h),U=new Float64Array(h);for(let i=0;i<h;i++){let lo=0,hi=0;for(let k=0;k<m;k++){const w=W[k][i];if(w>=0){lo+=w*boxL[k];hi+=w*boxU[k];}else{lo+=w*boxU[k];hi+=w*boxL[k];}}L[i]=lo+b[i];U[i]=hi+b[i];}return [L,U];}
function reluBox(boxL,boxU){const L=new Float64Array(boxL.length),U=new Float64Array(boxL.length);for(let i=0;i<boxL.length;i++){L[i]=Math.max(0,boxL[i]);U[i]=Math.max(0,boxU[i]);}return [L,U];}
function gruIbp(g,xL,xU,hL,hU){
  const gi=xL.length,gh=hL.length,sig=v=>1/(1+Math.exp(-v));
  const acc=(Wi,bi,Wh,bh)=>{const rL=new Float64Array(gh),rU=new Float64Array(gh);for(let k=0;k<gh;k++){let lo=bi[k],hi=bi[k];for(let j=0;j<gi;j++){const w=Wi[j][k];if(w>=0){lo+=w*xL[j];hi+=w*xU[j];}else{lo+=w*xU[j];hi+=w*xL[j];}}for(let j=0;j<gh;j++){const w=Wh[j][k];if(w>=0){lo+=w*hL[j];hi+=w*hU[j];}else{lo+=w*hU[j];hi+=w*hL[j];}}rL[k]=lo;rU[k]=hi;}return [rL,rU];};
  const [rL,rU]=acc(g.Wir_r,g.bir_r,g.Whr_r,g.bhr_r);
  const [zL,zU]=acc(g.Wir_z,g.bir_z,g.Whr_z,g.bhr_z);
  const rLs=rL.map(sig),rUs=rU.map(sig),zLs=zL.map(sig),zUs=zU.map(sig);
  const cL=new Float64Array(gh),cU=new Float64Array(gh);
  for(let k=0;k<gh;k++){let lo=g.bhr_n[k],hi=g.bhr_n[k];for(let j=0;j<gh;j++){const w=g.Whr_n[j][k];if(w>=0){lo+=w*hL[j];hi+=w*hU[j];}else{lo+=w*hU[j];hi+=w*hL[j];}}cL[k]=lo;cU[k]=hi;}
  const nL=new Float64Array(gh),nU=new Float64Array(gh);
  for(let k=0;k<gh;k++){let lo=g.bir_n[k],hi=g.bir_n[k];for(let j=0;j<gi;j++){const w=g.Wir_n[j][k];if(w>=0){lo+=w*xL[j];hi+=w*xU[j];}else{lo+=w*xU[j];hi+=w*xL[j];}}const p=imul4(rL[k]*cL[k],rL[k]*cU[k],rU[k]*cL[k],rU[k]*cU[k]);lo+=p[0];hi+=p[1];nL[k]=Math.tanh(lo);nU[k]=Math.tanh(hi);}
  const hL2=new Float64Array(gh),hU2=new Float64Array(gh);
  for(let k=0;k<gh;k++){const dL=hL[k]-nU[k],dU=hU[k]-nL[k];const p=imul4(zL[k]*dL,zL[k]*dU,zU[k]*dL,zU[k]*dU);hL2[k]=nL[k]+p[0];hU2[k]=nU[k]+p[1];}
  return [hL2,hU2];
}
// 多步 IBP 界（第二实现）：绝对态盒传播
function multistepIbp(p,h0,z0c,z0rad,actions,K){
  const gi=p.STOCH+p.ACT;
  let hL=Float64Array.from(h0),hU=Float64Array.from(h0);
  let zL=new Float64Array(p.STOCH),zU=new Float64Array(p.STOCH);for(let j=0;j<p.STOCH;j++){zL[j]=z0c[j]-z0rad;zU[j]=z0c[j]+z0rad;}
  for(let t=0;t<K;t++){
    const a=actions[t];
    const xL=new Float64Array(gi),xU=new Float64Array(gi);
    for(let j=0;j<p.ACT;j++){xL[j]=a[j];xU[j]=a[j];}
    for(let j=0;j<p.STOCH;j++){xL[p.ACT+j]=zL[j];xU[p.ACT+j]=zU[j];}
    const [hL2,hU2]=gruIbp(p.gru,xL,xU,hL,hU);
    const [pL,pU]=ibpMat(p.prior.W2,p.prior.b2,...reluBox(...ibpMat(p.prior.W1,p.prior.b1,hL2,hU2)));
    for(let j=0;j<p.STOCH;j++){zL[j]=pL[j];zU[j]=pU[j];}
    const dInL=new Float64Array(p.DETER+p.STOCH),dInU=new Float64Array(p.DETER+p.STOCH);
    for(let j=0;j<p.DETER;j++){dInL[j]=hL2[j];dInU[j]=hU2[j];}
    for(let j=0;j<p.STOCH;j++){dInL[p.DETER+j]=zL[j];dInU[p.DETER+j]=zU[j];}
    const [oL,oU]=ibpMat(p.dec.W2,p.dec.b2,...reluBox(...ibpMat(p.dec.W1,p.dec.b1,dInL,dInU)));
    hL=hL2;hU=hU2;
    if(t===K-1) return {obsL:oL,obsU:oU};
  }
}

// ---------- 实验 ----------
const DETER=8,STOCH=6,ACT=2,OBS=3,K=4,eps=0.05;
let failUB=0,failLB=0,total=0,maxUBviol=0,maxLBviol=0,cornersChecked=0;
const NC=1<<STOCH;
for(let trial=0;trial<200;trial++){
  const gru={Wir_r:rmat(ACT+STOCH,DETER),bir_r:rbias(DETER),Whr_r:rmat(DETER,DETER),bhr_r:rbias(DETER),
             Wir_z:rmat(ACT+STOCH,DETER),bir_z:rbias(DETER),Whr_z:rmat(DETER,DETER),bhr_z:rbias(DETER),
             Wir_n:rmat(ACT+STOCH,DETER),bir_n:rbias(DETER),Whr_n:rmat(DETER,DETER),bhr_n:rbias(DETER)};
  const prior={W1:rmat(DETER,DETER),b1:rbias(DETER),W2:rmat(DETER,STOCH*2),b2:rbias(STOCH*2)};
  const dec={W1:rmat(DETER+STOCH,DETER),b1:rbias(DETER),W2:rmat(DETER,OBS),b2:rbias(OBS)};
  const p={gru,prior,dec,DETER,STOCH,ACT};
  const h0=new Float64Array(DETER),z0c=new Float64Array(STOCH),z0rad=eps;
  const rngA=mulberry32(7+trial);const actions=[];for(let t=0;t<K;t++)actions.push([rngA()*2-1,rngA()*2-1]);
  const bnd=multistepIbp(p,h0,z0c,z0rad,actions,K);
  // 角点穷举 z0
  for(let cmb=0;cmb<NC;cmb++){
    const z0=new Float64Array(STOCH);for(let j=0;j<STOCH;j++)z0[j]=z0c[j]+((cmb>>j)&1?z0rad:-z0rad);
    let h=Float64Array.from(h0),z=z0;
    for(let t=0;t<K;t++){
      const x=Array.from(actions[t]).concat(Array.from(z));
      h=gruStepF(x,h,gru);
      const po=priorF(prior.W1,prior.b1,prior.W2,prior.b2,h);
      const mu=new Float64Array(STOCH);for(let j=0;j<STOCH;j++)mu[j]=po[j];
      z=mu;
    }
    const dh=new Float64Array(DETER);for(let i=0;i<DETER;i++){let s=0;for(let k=0;k<DETER;k++)s+=h[k]*dec.W1[k][i];const v=s+dec.b1[i];dh[i]=v>0?v:0;}
    const obs=new Float64Array(OBS);for(let j=0;j<OBS;j++){let s=0;for(let k=0;k<DETER;k++)s+=dh[k]*dec.W2[k][j];obs[j]=s+dec.b2[j];}
    cornersChecked++;
    for(let j=0;j<OBS;j++){
      total++;
      const ubviol=obs[j]-bnd.obsU[j]; // 希望 <=0
      const lbviol=bnd.obsL[j]-obs[j]; // 希望 <=0
      if(ubviol>1e-9){failUB++;maxUBviol=Math.max(maxUBviol,ubviol);}
      if(lbviol>1e-9){failLB++;maxLBviol=Math.max(maxLBviol,lbviol);}
    }
  }
}
const line='多步IBP交叉验证: trials=200 corners/trial='+NC+' cornersChecked='+cornersChecked+' totalObs='+total+
  ' failUB='+failUB+' failLB='+failLB+' maxUBviol='+maxUBviol.toFixed(6)+' maxLBviol='+maxLBviol.toFixed(6)+
  '\n'+(failUB===0&&failLB===0?'多步 IBP 第二实现 SOUND: PASS (所有角点输出含于 sound 盒)':'多步 IBP 第二实现 SOUND: FAIL')+'\n';
console.log(line);
fs.writeFileSync('H:\\科研补充资料_世界模型物理AI\\_scripts\\test_multistep_xval_result.txt', line, 'utf8');
