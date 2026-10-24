// Transcribed from retained Unreal material expressions; positions are pre-skinned cm.
// Source snapshot: Avatar main a204705. Never execute material source from a network response.
export const familySurface = `
float familyClamp(float x){return clamp(x,0.0,1.0);}
vec3 noaCloth(vec3 P){vec2 p=P.xz-vec2(0.0,4.4);
float front=smoothstep(1.5,4.0,P.y);
float torso=(1.0-smoothstep(17.0,20.0,abs(p.x)))*smoothstep(108.0,112.0,p.y)*(1.0-smoothstep(143.0,148.0,p.y))*front;
float center=1.0-smoothstep(.025,.065,abs(p.x-(1.0+3.0*smoothstep(121.0,148.0,p.y))));
float seam=1.0-smoothstep(.035,.095,abs(abs(p.x)-(12.5+1.2*smoothstep(132.0,147.0,p.y))));
vec2 q=p-vec2(-7.0,136.0);
float ring=1.0-smoothstep(.035,.09,abs(length(q)-2.6));
float d=abs(q.x); float branches=0.0;
for(float i=0.0;i<6.0;i++){
 float side=i<3.0?-1.0:1.0;float row=mod(i,3.0);vec2 a=vec2(0.0,-1.2+row*.95);vec2 b=vec2(side*(1.5-row*.2),-.5+row*.95);
 vec2 ba=b-a;vec2 v=q-a;float dist=length(v-ba*familyClamp(dot(v,ba)/dot(ba,ba)));
 branches=max(branches,1.0-smoothstep(.045,.09,dist));
 branches=max(branches,1.0-smoothstep(.10,.15,length(q-b)));
}
float stem=(1.0-smoothstep(.045,.09,d))*(1.0-smoothstep(1.8,2.0,abs(q.y)));
vec2 b=p-vec2(11.5,145.8);
float lattice=0.0;
for(float i=0.0;i<5.0;i++){
 vec2 c=vec2(sin(i*2.1)*2.0,cos(i*2.1)*2.5);
 lattice=max(lattice,1.0-smoothstep(.065,.13,length(b-c)));
 vec2 ba=c;float dist=length(b-ba*familyClamp(dot(b,ba)/max(dot(ba,ba),.001)));
 lattice=max(lattice,(1.0-smoothstep(.020,.045,dist))*.6);
}
float detail=familyClamp(lattice*front*.5+(center*.20+seam*.28+(ring*.65+max(branches,stem)*.85))*torso);
vec3 dye=mix(mix(vec3(.005,.014,.022),vec3(.009,.022,.030),smoothstep(10.0,16.0,abs(p.x))),vec3(.023,.658,.584),detail);
vec2 threads=P.xz*21.0;float fade=1.0-smoothstep(.7,2.5,max(fwidth(threads.x),fwidth(threads.y)));
return dye*(1.0+.025*sin(threads.x)*sin(threads.y)*fade);}
vec2 noaSleeves(vec3 P){vec3 Q=vec3(abs(P.x),P.y,P.z);float t=dot(Q-vec3(45.34694494010456,15.727310135319355,104.07102683496463),vec3(0.5040975789228932,0.6173149707333802,-0.6039932597575269));float arm=smoothstep(15.0,18.0,Q.x)*smoothstep(65.0,75.0,Q.z);return vec2((1.0-smoothstep(-.25,.05,t))*arm,(smoothstep(-1.2,-.9,t)-smoothstep(-.65,-.35,t))*arm);}
vec3 novaCloth(vec3 P){float front=smoothstep(1.,5.,P.y);
float torso=(1.0-smoothstep(17.,20.,abs(P.x)))*smoothstep(100.,106.,P.z)*(1.0-smoothstep(143.,147.,P.z))*front;
float center=1.0-smoothstep(.045,.12,abs(P.x));
float st=12.+2.8*smoothstep(134.,146.,P.z);
float edge=1.0-smoothstep(.045,.11,abs(abs(P.x)-st));
float edge2=1.0-smoothstep(.03,.08,abs(abs(P.x)-st-1.));
vec2 q=vec2(P.x+7.,P.z-135.);
float a=atan(q.y,q.x);float r=length(q);
float radius=mix(.55,2.15,pow(abs(cos(a*4.)),7.));
float star=(1.0-smoothstep(radius-.04,radius+.04,r));
float ring=1.0-smoothstep(.025,.075,abs(r-2.45));
float lines=familyClamp((center*.18+(edge+.3*edge2)*.4*smoothstep(111.,119.,P.z)+star*.85+ring*.45)*torso);
float panel=smoothstep(10.5,13.,abs(P.x))*torso;
return mix(mix(vec3(.009,.019,.04),vec3(.004,.008,.02),panel),vec3(.83,.52,.12),lines);}
float atlasLines(vec3 P){
float front=smoothstep(1.0,4.0,P.y);
float torso=smoothstep(110.0,114.0,P.z)*(1.0-smoothstep(159.0,164.0,P.z))*(1.0-smoothstep(17.0,22.0,abs(P.x)))*front;
float path=11.5+3.0*smoothstep(140.0,158.0,P.z);
float seam=1.0-smoothstep(.07,.17,abs(abs(P.x)-path));
float parallel=(1.0-smoothstep(.03,.11,abs(abs(P.x)-path-.85)))*smoothstep(142.0,144.0,P.z);
float branch=(1.0-smoothstep(.055,.14,abs(P.z-(149.0+1.3*(abs(P.x)-12.0)))))*smoothstep(12.0,12.3,abs(P.x))*(1.0-smoothstep(16.0,16.3,abs(P.x)));
vec2 q=vec2(P.x+7.2,P.z-150.5);
float r=length(q),a=atan(q.y,q.x);
float hex=1.0-smoothstep(.055,.13,abs(r-(2.0+.20*pow(abs(cos(a*6.0)),8.))));
float inner=max(1.0-smoothstep(.045,.12,abs(length(vec2(q.x*.85,q.y*.6))-.70)),(1.0-smoothstep(.04,.10,abs(q.x-q.y*.35)))*(1.0-smoothstep(.9,1.1,abs(q.y))));
float zip=(1.0-smoothstep(.025,.075,abs(P.x)))*.22;
return familyClamp((seam*.58+parallel*.28+zip+hex*.85+inner*.65)*torso);
}
vec3 atlasCloth(vec3 P){float L=atlasLines(P);float side=smoothstep(12.0,19.0,abs(P.x)); vec3 fabric=mix(vec3(.008,.055,.032),vec3(.004,.024,.015),side);fabric=mix(fabric,vec3(.004,.009,.008),1.0-smoothstep(97.0,99.0,P.z));return mix(fabric,vec3(.10,.58,.31),L);}
vec3 atlasSkin(vec3 P,vec3 C){
float x=abs(P.x),z=P.z,front=smoothstep(3.5,7.5,P.y);
float jawTop=166.9+0.88*x;
float jaw=smoothstep(161.7,163.8,z)*(1.0-smoothstep(jawTop-.6,jawTop+.85,z));
float sideburn=smoothstep(6.0,7.0,x)*(1.0-smoothstep(7.6,8.7,x))*smoothstep(165.0,167.0,z)*(1.0-smoothstep(175.5,177.,z));
float moustache=(1.0-smoothstep(2.4,3.05,x))*smoothstep(169.45,169.9,z)*(1.0-smoothstep(171.0,171.4,z));
float lips=1.0-smoothstep(.88,1.10,length(vec2(P.x/2.45,(z-168.65)/1.35)));
float mask=familyClamp(max(max(jaw,sideburn),moustache))*front*(1.0-lips);
float grain=fract(sin(dot(floor(P*vec3(120.0,120.0,170.0)),vec3(12.9898,78.233,39.425)))*43758.5453);
float strand=pow(familyClamp(.5+.5*sin(P.x*155.0+sin(P.z*25.0)*2.)),8.);
vec3 beard=mix(vec3(.082,.088,.092),vec3(.16,.172,.18),smoothstep(.45,.88,grain));
beard=mix(beard,vec3(.20,.21,.22),strand*.12);
vec3 result=mix(C*vec3(.98,.94,.90),beard,mask*.76);
float forehead=0.0;
for(float k=0.0;k<3.0;k++){float wrinkleZ=180.6+k*.88+.025*x*x;forehead=max(forehead,(1.0-smoothstep(.025,.095,abs(z-wrinkleZ)))*(1.0-smoothstep(4.3,5.8,x)));}
float underEye=(1.0-smoothstep(.03,.14,abs(z-(174.65+.10*(x-3.5)*(x-3.5)))))*smoothstep(1.7,2.5,x)*(1.0-smoothstep(5.0,5.8,x));
float smile=(1.0-smoothstep(.04,.16,abs(x-(2.7+.19*(172.5-z)))))*smoothstep(168.2,169.4,z)*(1.0-smoothstep(172.2,173.0,z));
float crease=max(forehead*.07,max(underEye*.18,smile*.18))*front;
vec3 lipColor=mix(result,vec3(dot(result,vec3(.30,.59,.11))),.35)*.94;
result=mix(result,lipColor,lips);
return result*(1.0-crease);
}

float familySegment(vec2 p,vec2 a,vec2 b){vec2 v=b-a;return length(p-a-v*clamp(dot(p-a,v)/dot(v,v),0.0,1.0));}
float familyTraces(vec3 P){
  vec2 p=vec2(abs(P.x/20.0),.5+(162.5-P.z)/28.0);
  float d=1.0;
  d=min(d,familySegment(p,vec2(.24,.16),vec2(.24,.26)));
  d=min(d,familySegment(p,vec2(.24,.26),vec2(.30,.31)));
  d=min(d,familySegment(p,vec2(.30,.31),vec2(.30,.37)));
  d=min(d,familySegment(p,vec2(.32,.42),vec2(.23,.48)));
  d=min(d,familySegment(p,vec2(.23,.48),vec2(.23,.57)));
  d=min(d,familySegment(p,vec2(.23,.57),vec2(.27,.61)));
  d=min(d,familySegment(p,vec2(.27,.64),vec2(.25,.69)));
  d=min(d,min(abs(length(p-vec2(.24,.16))-.004),abs(length(p-vec2(.25,.69))-.004)));
  return (1.0-smoothstep(.0012,max(.0025,fwidth(d)),d))*.65*smoothstep(0.0,2.0,P.y);
}`;
