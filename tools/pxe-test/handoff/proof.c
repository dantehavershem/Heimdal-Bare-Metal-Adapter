/* Disposable-VM handoff proof. UEFI runtime table layout follows UEFI 2.x. */
typedef unsigned char U8;
typedef unsigned short U16;
typedef unsigned int U32;
typedef unsigned long long U64;
typedef U64 Status;
typedef struct {U32 a;U16 b,c;U8 d[8];} Guid;
typedef struct {U64 sig;U32 rev,size,crc,reserved;} Header;
typedef struct {
 Header hdr;
 void *clock[6];
 Status (*GetVariable)(U16*,Guid*,U32*,U64*,void*);
 void *GetNextVariableName;
 Status (*SetVariable)(U16*,Guid*,U32,U64,void*);
} Runtime;
typedef struct {
 Header hdr; U16*vendor;U32 revision;
 void *inHandle,*in,*outHandle,*out,*errHandle,*err;
 Runtime*rt;void*bs;U64 tables;void*table;
} System;
static Guid global={0x8be4df61,0x93ca,0x11d2,{0xaa,0x0d,0x00,0xe0,0x98,0x03,0x2b,0x8c}};
static Guid audit={0x707b6e82,0x73fd,0x42ba,{0x85,0xbf,0x18,0x7c,0xd2,0x84,0x1b,0x37}};
static U8 snapshot[516],order[512];
static void log(const char*s){while(*s)__asm__ volatile("outb %0,%1"::"a"((U8)*s++),"Nd"((U16)0xe9));}
static void stop(U8 code){__asm__ volatile("outb %0,%1"::"a"(code),"Nd"((U16)0xf4));for(;;)__asm__ volatile("hlt");}
#ifdef UBUNTU_TEST
#include "chainload.h"
#endif
Status efi_main(void *image,System *st){
 (void)image;
 U64 n=sizeof(snapshot),m=sizeof(order);U32 attrs;
 log("BMA_HANDOFF_UEFI_REACHED\n");
 if(st->rt->GetVariable((U16*)L"BmaBootAudit",&audit,&attrs,&n,snapshot)||n<6)goto failed;
 if(st->rt->GetVariable((U16*)L"BootOrder",&global,&attrs,&m,order)||m!=n-4)goto failed;
 if(m!=(U64)(snapshot[2]+256*snapshot[3]))goto failed;
 for(U64 i=0;i<m;i++)if(order[i]!=snapshot[i+4])goto failed;
 log("BMA_HANDOFF_BOOTORDER_PRESERVED\n");
 m=sizeof(order);
 if(st->rt->GetVariable((U16*)L"BootNext",&global,&attrs,&m,order)!=0x800000000000000eULL)goto failed;
 log("BMA_HANDOFF_BOOTNEXT_CONSUMED\n");
 m=sizeof(order);
 if(st->rt->GetVariable((U16*)L"BootCurrent",&global,&attrs,&m,order)||m!=2||order[0]!=snapshot[0]||order[1]!=snapshot[1])goto failed;
 log("BMA_HANDOFF_BOOTCURRENT_MATCHED\n");
 U16 name[]=L"Boot0000",hex[]=L"0123456789ABCDEF";
 U16 index=snapshot[0]+256*snapshot[1];
 for(int i=7;i>=4;i--){name[i]=hex[index&15];index>>=4;}
 if(st->rt->SetVariable(name,&global,7,0,0))goto failed;
 if(st->rt->SetVariable((U16*)L"BmaBootAudit",&audit,7,0,0))goto failed;
 m=sizeof(order);
 if(st->rt->GetVariable(name,&global,&attrs,&m,order)!=0x800000000000000eULL)goto failed;
 m=sizeof(order);
 if(st->rt->GetVariable((U16*)L"BmaBootAudit",&audit,&attrs,&m,order)!=0x800000000000000eULL)goto failed;
 log("BMA_HANDOFF_VARIABLES_CLEANED\n");
 log("BMA_HANDOFF_PROOF_PASSED\n");
#ifdef UBUNTU_TEST
 chainload(image,st);
#else
 stop(0x10);
#endif
failed:
 log("BMA_HANDOFF_PROOF_FAILED\n");stop(0x11);
 return 0;
}
