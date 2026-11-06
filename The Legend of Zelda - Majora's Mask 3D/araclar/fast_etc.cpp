#include <cstdint>
#include <cmath>
#include <algorithm>
#include <climits>
static int mods[8][4]={{2,8,-2,-8},{5,17,-5,-17},{9,29,-9,-29},{13,42,-13,-42},{18,60,-18,-60},{24,80,-24,-80},{33,106,-33,-106},{47,183,-47,-183}};
static int clamp(int x){return std::max(0,std::min(255,x));}
struct Fit {long long error=LLONG_MAX;int r,g,b,t;int s[16]={};};
static Fit fit(const uint8_t* p,int flip,int half){
 int ids[8],n=0; double sum[3]={},weight=0;
 for(int y=0;y<4;y++)for(int x=0;x<4;x++)if((flip?(y>=2):(x>=2))==half){int i=y*4+x;ids[n++]=i;double a=p[i*4+3]/255.;weight+=a;for(int c=0;c<3;c++)sum[c]+=p[i*4+c]*a;}
 int q[3];for(int c=0;c<3;c++)q[c]=weight?std::round(sum[c]/weight/17):0;
 Fit best;
 for(int r=std::max(0,q[0]-2);r<=std::min(15,q[0]+2);r++)for(int g=std::max(0,q[1]-2);g<=std::min(15,q[1]+2);g++)for(int b=std::max(0,q[2]-2);b<=std::min(15,q[2]+2);b++)for(int t=0;t<8;t++){
  long long err=0;int sels[16]={};
  for(int j=0;j<n;j++){int i=ids[j];int mine=INT_MAX,sel=0;for(int s=0;s<4;s++){int dr=p[4*i]-clamp(r*17+mods[t][s]),dg=p[4*i+1]-clamp(g*17+mods[t][s]),db=p[4*i+2]-clamp(b*17+mods[t][s]);int e=dr*dr+dg*dg+db*db;if(e<mine){mine=e;sel=s;}}err+=(long long)mine*p[i*4+3];sels[i]=sel;if(err>=best.error)break;}
  if(err<best.error){best.error=err;best.r=r;best.g=g;best.b=b;best.t=t;std::copy(sels,sels+16,best.s);}
 }return best;
}
extern "C" uint64_t encode_block(const uint8_t* p){
 uint64_t out=0;long long best=LLONG_MAX;
 for(int flip=0;flip<2;flip++){Fit a=fit(p,flip,0),b=fit(p,flip,1);if(a.error+b.error>=best)continue;best=a.error+b.error;
  uint64_t w=(uint64_t(a.r)<<60)|(uint64_t(b.r)<<56)|(uint64_t(a.g)<<52)|(uint64_t(b.g)<<48)|(uint64_t(a.b)<<44)|(uint64_t(b.b)<<40)|(uint64_t(a.t)<<37)|(uint64_t(b.t)<<34)|(uint64_t(flip)<<32);
  for(int y=0;y<4;y++)for(int x=0;x<4;x++){int s=(flip?(y<2):(x<2))?a.s[y*4+x]:b.s[y*4+x];int k=x*4+y;w|=uint64_t(s&1)<<k;w|=uint64_t((s>>1)&1)<<(16+k);}out=w;
 }return out;
}
