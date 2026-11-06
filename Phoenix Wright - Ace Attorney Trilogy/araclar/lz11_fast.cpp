#include <bits/stdc++.h>
using namespace std;
static inline uint32_t key3(const vector<uint8_t>& d,size_t p){return (uint32_t(d[p])<<16)|(uint32_t(d[p+1])<<8)|d[p+2];}
int main(int argc,char**argv){
 if(argc!=3){cerr<<"usage: lz11_fast input output\n";return 2;}
 ifstream f(argv[1],ios::binary); if(!f){cerr<<"input open failed\n";return 2;}
 vector<uint8_t>d((istreambuf_iterator<char>(f)),{}); vector<uint8_t>o;
 size_t n=d.size(); if(n>=0x1000000){o={0x11,0,0,0}; uint32_t x=n; for(int i=0;i<4;i++)o.push_back((x>>(8*i))&255);}else{o={0x11,uint8_t(n),uint8_t(n>>8),uint8_t(n>>16)};}
 unordered_map<uint32_t,deque<int>> tab; tab.reserve(1<<16);
 auto addpos=[&](int p){ if(p+3>(int)n)return; auto &q=tab[key3(d,p)]; q.push_back(p); while(!q.empty() && p-q.front()>4096)q.pop_front();};
 size_t p=0;
 while(p<n){size_t fp=o.size();o.push_back(0);uint8_t flags=0;
  for(int bit=0;bit<8 && p<n;bit++){
   int best=0,disp=0;
   if(p+3<=n){auto it=tab.find(key3(d,p)); if(it!=tab.end()){int checked=0;auto &q=it->second;for(auto ri=q.rbegin();ri!=q.rend();++ri){int prev=*ri;int dd=(int)p-prev;if(dd>4096)break;if(++checked>4)break;int lim=min<size_t>(0x10110,n-p);int l=3;while(l<lim && d[prev+l]==d[p+l])l++;if(l>best){best=l;disp=dd;if(l==lim)break;}}}}
   if(best>=3){flags|=(0x80>>bit);int dd=disp-1;
    if(best<=0x10){o.push_back(((best-1)<<4)|((dd>>8)&0xF));o.push_back(dd&0xFF);}
    else if(best<=0x110){int x=best-0x11;o.push_back((x>>4)&0xF);o.push_back(((x&0xF)<<4)|((dd>>8)&0xF));o.push_back(dd&0xFF);}
    else {int x=best-0x111;o.push_back(0x10|((x>>12)&0xF));o.push_back((x>>4)&0xFF);o.push_back(((x&0xF)<<4)|((dd>>8)&0xF));o.push_back(dd&0xFF);}
    for(int j=0;j<best;j++)addpos((int)p+j);p+=best;
   } else {o.push_back(d[p]);addpos((int)p);p++;}
  }
  o[fp]=flags;
 }
 ofstream g(argv[2],ios::binary);g.write((char*)o.data(),o.size());cerr<<"input="<<n<<" output="<<o.size()<<"\n";
}
