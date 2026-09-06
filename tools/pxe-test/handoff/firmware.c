/* LAB ONLY: run from the generated capsule in a disposable UEFI WinPE VM.
 * Creates an unused BootXXXX plus BootNext, never writes BootOrder.
 * The capsule supplies a GPT partition device path for its unique staging disk.
 */
typedef unsigned long DWORD;
typedef unsigned short WORD;
typedef unsigned char BYTE;
typedef int BOOL;
typedef void *HANDLE;
typedef unsigned short WCHAR;
#define API __declspec(dllimport)
#define W(s) ((const WCHAR*)L##s)
API DWORD GetFileAttributesW(const WCHAR*);
API DWORD GetEnvironmentVariableW(const WCHAR*,WCHAR*,DWORD);
API HANDLE GetCurrentProcess(void);
API BOOL OpenProcessToken(HANDLE,DWORD,HANDLE*);
API BOOL LookupPrivilegeValueW(const WCHAR*,const WCHAR*,void*);
API BOOL AdjustTokenPrivileges(HANDLE,BOOL,void*,DWORD,void*,DWORD*);
API DWORD GetLastError(void);
API void SetLastError(DWORD);
API DWORD GetFirmwareEnvironmentVariableW(const WCHAR*,const WCHAR*,void*,DWORD);
API BOOL SetFirmwareEnvironmentVariableExW(const WCHAR*,const WCHAR*,void*,DWORD,DWORD);
API HANDLE CreateFileW(const WCHAR*,DWORD,DWORD,void*,DWORD,DWORD,HANDLE);
API BOOL ReadFile(HANDLE,void*,DWORD,DWORD*,void*);
API BOOL WriteFile(HANDLE,const void*,DWORD,DWORD*,void*);
API BOOL CloseHandle(HANDLE);
API void ExitProcess(DWORD);
static const WCHAR *global=W("{8be4df61-93ca-11d2-aa0d-00e098032b8c}");
static const WCHAR *audit=W("{707b6e82-73fd-42ba-85bf-187cd2841b37}");
static BYTE option[512], order[512], check[512], snapshot[516];
static WCHAR name[]=L"BootB000";
static void log(const char *s) {
    DWORD n=0,written; while(s[n])n++;
    HANDLE h=CreateFileW(W("COM1"),0x40000000,0,0,3,0,0);
    if(h!=(HANDLE)-1){WriteFile(h,s,n,&written,0);CloseHandle(h);}
}
static void fail(DWORD code) {
    char msg[]="BMA_HANDOFF_FAILED code=000 winerror=0000000000\r\n";
    DWORD err=GetLastError();
    for(int i=46;i>=37;i--){msg[i]=(char)('0'+err%10);err/=10;}
    for(int i=26;i>=24;i--){msg[i]=(char)('0'+code%10);code/=10;}
    log(msg); ExitProcess(1);
}
static BOOL same(BYTE*a,BYTE*b,DWORD n){for(DWORD i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static BYTE copy_a[2048],copy_b[2048];
static void verify_copy(const WCHAR *source,const WCHAR *destination) {
    HANDLE a=CreateFileW(source,0x80000000,1,0,3,0,0);
    HANDLE b=CreateFileW(destination,0x80000000,1,0,3,0,0);
    if(a==(HANDLE)-1 || b==(HANDLE)-1)fail(30);
    DWORD na,nb; BOOL first=1;
    do {
        if(!ReadFile(a,copy_a,sizeof(copy_a),&na,0) || !ReadFile(b,copy_b,sizeof(copy_b),&nb,0))fail(31);
        if(na!=nb || !same(copy_a,copy_b,na))fail(32);
        if(first){
            if(na<128 || copy_a[0]!='M' || copy_a[1]!='Z')fail(35);
            DWORD pe=*(DWORD*)(copy_a+0x3c);
            if(pe>na-94 || *(DWORD*)(copy_a+pe)!=0x4550 || *(WORD*)(copy_a+pe+4)!=0x8664 ||
               *(WORD*)(copy_a+pe+24)!=0x20b || *(WORD*)(copy_a+pe+92)!=10)fail(35);
            first=0;
        }
    } while(na);
    CloseHandle(a);CloseHandle(b);
}
void mainCRTStartup(void) {
    WCHAR drive[4],target[]=L"S:\\EFI\\BMA\\stage.efi";
    if(GetEnvironmentVariableW(W("BMA_TARGET"),drive,4)!=2 || drive[0]<'C' || drive[0]>'Z' || drive[1]!=':')fail(33);
    target[0]=drive[0];
    verify_copy(W("runtime\\stage.efi"),target);
    if(GetFileAttributesW(W("runtime\\grub.efi"))!=0xffffffffUL){
        WCHAR grub[]=L"S:\\EFI\\BMA\\grub.efi";grub[0]=drive[0];
        verify_copy(W("runtime\\grub.efi"),grub);
    } else if(GetLastError()!=2)fail(34);
    HANDLE token; DWORD got,attr=7;
    struct { DWORD count; DWORD low; long high; DWORD attributes; } privilege={1,0,0,2};
    if(!OpenProcessToken(GetCurrentProcess(),0x28,&token))fail(10);
    if(!LookupPrivilegeValueW(0,W("SeSystemEnvironmentPrivilege"),&privilege.low))fail(11);
    SetLastError(0);
    if(!AdjustTokenPrivileges(token,0,&privilege,0,0,0)||GetLastError())fail(12);
    CloseHandle(token);
    if(GetFirmwareEnvironmentVariableW(W("BootNext"),global,check,sizeof(check)) || GetLastError()!=203)fail(13);
    if(GetFirmwareEnvironmentVariableW(W("BmaBootAudit"),audit,check,sizeof(check)) || GetLastError()!=203)fail(14);
    DWORD len=GetFirmwareEnvironmentVariableW(W("BootOrder"),global,order,sizeof(order));
    if(!len || len>512 || len%2)fail(15);
    HANDLE file=CreateFileW(W("runtime\\boot-option.bin"),0x80000000,1,0,3,0,0);
    if(file==(HANDLE)-1)fail(16);
    BOOL read=ReadFile(file,option,sizeof(option),&got,0); CloseHandle(file);
    if(!read || got<50 || got>=512 || option[0]!=1)fail(17);
    WORD index=0;
    const WCHAR hex[]=L"0123456789ABCDEF";
    for(DWORD i=0xb000;i<0xb100;i++){
        name[6]=hex[(i>>4)&15]; name[7]=hex[i&15];
        if(!GetFirmwareEnvironmentVariableW(name,global,check,sizeof(check)) && GetLastError()==203){index=(WORD)i;break;}
    }
    if(!index)fail(18);
    snapshot[0]=(BYTE)index;snapshot[1]=(BYTE)(index>>8);
    snapshot[2]=(BYTE)len;snapshot[3]=(BYTE)(len>>8);
    for(DWORD i=0;i<len;i++)snapshot[i+4]=order[i];
    if(!SetFirmwareEnvironmentVariableExW(W("BmaBootAudit"),audit,snapshot,len+4,attr))fail(19);
    if(!SetFirmwareEnvironmentVariableExW(name,global,option,got,attr))goto rollback;
    if(GetFirmwareEnvironmentVariableW(name,global,check,sizeof(check))!=got || !same(option,check,got))goto rollback;
    if(!SetFirmwareEnvironmentVariableExW(W("BootNext"),global,&index,2,attr))goto rollback;
    if(GetFirmwareEnvironmentVariableW(W("BootNext"),global,check,sizeof(check))!=2 || check[0]!=(BYTE)index || check[1]!=(BYTE)(index>>8))goto rollback_next;
    if(GetFirmwareEnvironmentVariableW(W("BootOrder"),global,check,sizeof(check))!=len || !same(order,check,len))goto rollback_next;
    log("BMA_HANDOFF_BOOTNEXT_SET\r\n");
    log("BMA_HANDOFF_BOOTORDER_UNCHANGED\r\n");
    ExitProcess(0);
rollback_next:
    SetFirmwareEnvironmentVariableExW(W("BootNext"),global,0,0,attr);
rollback:
    SetFirmwareEnvironmentVariableExW(name,global,0,0,attr);
    SetFirmwareEnvironmentVariableExW(W("BmaBootAudit"),audit,0,0,attr);
    fail(20);
}
