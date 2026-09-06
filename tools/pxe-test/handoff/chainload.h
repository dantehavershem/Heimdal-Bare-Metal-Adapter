/* Minimal UEFI Boot Services subset for loading a file on our staging volume. */
typedef struct {
 Header hdr;
 void *tpl[2];
 void *pages[3];
 Status (*AllocatePool)(U32,U64,void**);
 Status (*FreePool)(void*);
 void *events[6];
 void *protocols[3];
 Status (*HandleProtocol)(void*,Guid*,void**);
 void *reserved,*notify,*locate,*devicepath,*configuration;
 Status (*LoadImage)(U8,void*,void*,void*,U64,void**);
 Status (*StartImage)(void*,U64*,U16**);
} Boot;
typedef struct {
 U32 revision;void *parent;System *system;void *device;void *path,*reserved;
 U32 optionsSize;void *options,*base;U64 size;U32 codeType,dataType;void *unload;
} LoadedImage;
static Guid loadedGuid={0x5b1b31a1,0x9562,0x11d2,{0x8e,0x3f,0x00,0xa0,0xc9,0x69,0x72,0x3b}};
static Guid pathGuid={0x09576e91,0x6d3f,0x11d2,{0x8e,0x39,0x00,0xa0,0xc9,0x69,0x72,0x3b}};
static void chainload(void *image,System *st) {
 Boot *bs=(Boot*)st->bs;LoadedImage *loaded;U8 *path,*next;void *child;
 if(bs->HandleProtocol(image,&loadedGuid,(void**)&loaded))goto failed;
 if(bs->HandleProtocol(loaded->device,&pathGuid,(void**)&path))goto failed;
 U64 offset=0;
 while(path[offset]!=0x7f){
  U16 len=path[offset+2]+256*path[offset+3];
  if(len<4 || offset+len>4096)goto failed;
  offset+=len;
 }
 U16 file[]=L"\\EFI\\BMA\\grub.efi";
 U64 nodeSize=4+sizeof(file),total=offset+nodeSize+4;
 if(bs->AllocatePool(2,total,(void**)&next))goto failed;
 for(U64 i=0;i<offset;i++)next[i]=path[i];
 next[offset]=4;next[offset+1]=4;next[offset+2]=(U8)nodeSize;next[offset+3]=(U8)(nodeSize>>8);
 for(U64 i=0;i<sizeof(file);i++)next[offset+4+i]=((U8*)file)[i];
 next[total-4]=0x7f;next[total-3]=0xff;next[total-2]=4;next[total-1]=0;
 Status result=bs->LoadImage(0,image,next,0,0,&child);bs->FreePool(next);
 if(result)goto failed;
 log("BMA_UBUNTU_GRUB_LOADED\n");
 bs->StartImage(child,0,0);
failed:
 log("BMA_UBUNTU_CHAINLOAD_FAILED\n");stop(0x12);
}
